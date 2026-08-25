"""apps/chat/serializers.py"""
from rest_framework import serializers
from .models import Conversation, Message, MessageFeedback


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = [
            "id", "role", "content", "cited_sources", "query_type",
            "confidence_score", "latency_ms", "feedback_rating", "created_at",
        ]
        read_only_fields = fields


class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ["id", "title", "message_count", "last_message_at", "created_at", "updated_at"]
        read_only_fields = fields


class ConversationListSerializer(serializers.ModelSerializer):
    last_message_preview = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ["id", "title", "message_count", "last_message_at", "last_message_preview", "created_at"]
        read_only_fields = fields

    def get_last_message_preview(self, obj):
        last = obj.messages.filter(role="assistant").order_by("-created_at").first()
        if last:
            return last.content[:100] + "..." if len(last.content) > 100 else last.content
        return None


class SendMessageSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=2000, required=True)
    filters = serializers.DictField(child=serializers.CharField(), required=False, default=dict)


class MessageFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageFeedback
        fields = ["rating", "feedback_type", "comment"]
