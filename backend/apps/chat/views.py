"""
apps/chat/views.py — AI Chatbot conversation endpoints with SSE streaming and synchronous JSON fallback.
"""
import json
import logging
from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.models import UserProfile
from core.permissions import IsCitizen
from core.utils import error_response, success_response
from rag.pipeline import RAGPipeline

from .models import Conversation, Message, MessageFeedback, MessageRole
from .serializers import (
    ConversationListSerializer,
    ConversationSerializer,
    MessageFeedbackSerializer,
    MessageSerializer,
    SendMessageSerializer,
)

logger = logging.getLogger(__name__)


class ConversationListCreateView(APIView):
    """
    GET  /api/v1/chat/conversations/ — List user's conversations
    POST /api/v1/chat/conversations/ — Create new conversation session
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        conversations = (
            Conversation.objects.filter(user=request.user, is_archived=False)
            .order_by("-updated_at")[:50]
        )
        serializer = ConversationListSerializer(conversations, many=True)
        return Response(success_response(data=serializer.data))

    def post(self, request):
        profile_snapshot = {}
        try:
            profile = UserProfile.objects.get(user=request.user)
            profile_snapshot = profile.to_eligibility_context()
        except UserProfile.DoesNotExist:
            pass

        title = request.data.get("title", "").strip() or "New Conversation"

        conversation = Conversation.objects.create(
            user=request.user,
            title=title,
            user_context_snapshot=profile_snapshot,
        )
        return Response(
            success_response(
                data=ConversationSerializer(conversation).data,
                message="Conversation created successfully.",
            ),
            status=status.HTTP_201_CREATED,
        )


class ConversationDetailView(APIView):
    """
    GET    /api/v1/chat/conversations/{id}/ — Retrieve conversation history
    DELETE /api/v1/chat/conversations/{id}/ — Archive / Delete conversation
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, request, conv_id):
        try:
            return Conversation.objects.get(id=conv_id, user=request.user)
        except Conversation.DoesNotExist:
            return None

    def get(self, request, conv_id):
        conv = self.get_object(request, conv_id)
        if not conv:
            return Response(
                error_response(code="NOT_FOUND", message="Conversation not found."),
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = ConversationSerializer(conv)
        messages = Message.objects.filter(conversation=conv).order_by("created_at")
        return Response(
            success_response(
                data={
                    **serializer.data,
                    "messages": MessageSerializer(messages, many=True).data,
                }
            )
        )

    def delete(self, request, conv_id):
        conv = self.get_object(request, conv_id)
        if not conv:
            return Response(
                error_response(code="NOT_FOUND", message="Conversation not found."),
                status=status.HTTP_404_NOT_FOUND,
            )
        conv.delete()
        return Response(success_response(message="Conversation deleted successfully."))


class SendMessageView(APIView):
    """
    POST /api/v1/chat/conversations/{id}/messages/
    Processes user query through RAG pipeline.
    Supports SSE streaming (default) or synchronous JSON (`?stream=false` or `Accept: application/json`).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, conv_id):
        try:
            conversation = Conversation.objects.get(id=conv_id, user=request.user)
        except Conversation.DoesNotExist:
            return Response(
                error_response(code="NOT_FOUND", message="Conversation not found."),
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_query = serializer.validated_data["content"]
        filters = serializer.validated_data.get("filters", {})

        # 1. Save user message
        user_message = Message.objects.create(
            conversation=conversation,
            role=MessageRole.USER,
            content=user_query,
        )

        # 2. Update conversation metadata
        conversation.message_count += 2
        conversation.last_message_at = timezone.now()
        if not conversation.title or conversation.title == "New Conversation":
            conversation.title = user_query[:80]
        conversation.save(update_fields=["message_count", "last_message_at", "title"])

        # 3. Retrieve recent conversation history
        history = list(
            Message.objects.filter(conversation=conversation)
            .exclude(id=user_message.id)
            .order_by("-created_at")[:10]
            .values("role", "content")
        )
        history.reverse()

        # 4. Resolve user profile context
        user_profile = conversation.user_context_snapshot or {}

        try:
            profile = UserProfile.objects.get(user=request.user)
            fresh_profile = profile.to_eligibility_context()

            # Always prefer the latest profile data.
            if fresh_profile:
                user_profile = fresh_profile
                conversation.user_context_snapshot = fresh_profile
                conversation.save(update_fields=["user_context_snapshot"])

        except UserProfile.DoesNotExist:
            # Keep an empty profile if the user has no profile yet.
            user_profile = conversation.user_context_snapshot or {}

        # Check if streaming is requested
        stream_param = request.query_params.get("stream", "true").lower()
        if stream_param == "false":
            # Synchronous JSON response mode
            pipeline = RAGPipeline()
            result = pipeline.run(
                query=user_query,
                user_profile=user_profile,
                conversation_history=history,
                filters=filters or None,
            )

            assistant_message = Message.objects.create(
                conversation=conversation,
                role=MessageRole.ASSISTANT,
                content=result.answer,
                retrieved_chunks=result.retrieved_chunks,
                cited_sources=result.citations,
                query_type=result.query_type,
                confidence_score=result.confidence_score,
                latency_ms=result.latency_ms,
            )

            return Response(
                success_response(
                    data={
                        "message": MessageSerializer(assistant_message).data,
                        "eligibility_result": result.eligibility_result,
                        "confidence_score": result.confidence_score,
                    }
                ),
                status=status.HTTP_201_CREATED,
            )

        # SSE Streaming response mode
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=MessageRole.ASSISTANT,
            content="",
        )

        return StreamingHttpResponse(
            self._sse_stream(
                user_query=user_query,
                history=history,
                user_profile=user_profile,
                assistant_message=assistant_message,
                filters=filters,
            ),
            content_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    def _sse_stream(
        self,
        user_query: str,
        history: list,
        user_profile: dict,
        assistant_message: Message,
        filters: dict,
    ):
        """Generator yielding Server-Sent Events (SSE)."""
        pipeline = RAGPipeline()
        full_answer = ""
        final_data = {}

        try:
            for event in pipeline.run_stream(
                query=user_query,
                user_profile=user_profile,
                conversation_history=history,
                filters=filters or None,
            ):
                event_type = event.get("event", "message")
                event_data = event.get("data", {})

                if event_type == "token":
                    full_answer += event_data.get("text", "")

                if event_type == "done":
                    final_data = event_data

                yield f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"

            # Persist assistant message details
            assistant_message.content = final_data.get("full_answer", full_answer)
            assistant_message.cited_sources = final_data.get("citations", [])
            assistant_message.confidence_score = final_data.get("confidence_score")
            assistant_message.latency_ms = final_data.get("latency_ms")
            assistant_message.query_type = final_data.get("query_type", "")
            assistant_message.save(update_fields=[
                "content", "cited_sources", "confidence_score",
                "latency_ms", "query_type",
            ])

        except Exception as e:
            logger.exception("SSE stream error: %s", e)
            error_event = {"error": "Response generation failed. Please try again."}
            yield f"event: error\ndata: {json.dumps(error_event)}\n\n"
            assistant_message.content = "I encountered an error while retrieving official scheme information. Please try again."
            assistant_message.save(update_fields=["content"])


class MessageFeedbackView(APIView):
    """POST /api/v1/chat/messages/{id}/feedback/ — Submit rating/feedback on AI message."""
    permission_classes = [IsAuthenticated]

    def post(self, request, message_id):
        try:
            message = Message.objects.get(
                id=message_id,
                role=MessageRole.ASSISTANT,
                conversation__user=request.user,
            )
        except Message.DoesNotExist:
            return Response(
                error_response(code="NOT_FOUND", message="Message not found."),
                status=status.HTTP_404_NOT_FOUND,
            )

        if hasattr(message, "feedback"):
            return Response(
                error_response(code="ALREADY_RATED", message="You have already rated this message."),
                status=status.HTTP_409_CONFLICT,
            )

        serializer = MessageFeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        feedback = MessageFeedback.objects.create(
            message=message,
            user=request.user,
            rating=serializer.validated_data["rating"],
            feedback_type=serializer.validated_data.get("feedback_type", ""),
            comment=serializer.validated_data.get("comment", ""),
        )

        message.feedback_rating = feedback.rating
        message.save(update_fields=["feedback_rating"])

        return Response(
            success_response(message="Thank you for your feedback!"),
            status=status.HTTP_201_CREATED,
        )
