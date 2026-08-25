"""apps/analytics/views.py — Admin analytics dashboard"""
from django.db.models import Avg, Count, Q
from rest_framework import filters
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from core.permissions import IsAdmin
from core.utils import success_response
from core.pagination import StandardResultsPagination
from .models import QueryLog


class DashboardView(APIView):
    """GET /api/v1/analytics/dashboard/ — Admin aggregate KPI dashboard."""
    permission_classes = [IsAdmin]

    def get(self, request):
        from apps.chat.models import Message, Conversation
        from apps.authentication.models import CustomUser
        from apps.documents.models import GovDocument
        from apps.schemes.models import GovernmentScheme

        data = {
            "total_users": CustomUser.objects.filter(is_active=True).count(),
            "total_conversations": Conversation.objects.count(),
            "total_messages": Message.objects.filter(role="assistant").count(),
            "total_documents": GovDocument.objects.count(),
            "total_documents_indexed": GovDocument.objects.filter(status="COMPLETED").count(),
            "total_schemes": GovernmentScheme.objects.count(),
            "avg_confidence_score": Message.objects.filter(
                role="assistant", confidence_score__isnull=False
            ).aggregate(avg=Avg("confidence_score"))["avg"],
            "avg_latency_ms": Message.objects.filter(
                role="assistant", latency_ms__isnull=False
            ).aggregate(avg=Avg("latency_ms"))["avg"],
            "failed_queries": QueryLog.objects.filter(
                Q(faithfulness__lt=0.5) | Q(confidence_score=0)
            ).count(),
            "positive_feedback": Message.objects.filter(feedback_rating=1).count(),
            "negative_feedback": Message.objects.filter(feedback_rating=-1).count(),
        }
        return Response(success_response(data=data))


class RAGMetricsView(APIView):
    """GET /api/v1/analytics/rag-metrics/ — RAGAS offline evaluation metrics."""
    permission_classes = [IsAdmin]

    def get(self, request):
        logs = QueryLog.objects.filter(faithfulness__isnull=False)
        metrics = logs.aggregate(
            avg_faithfulness=Avg("faithfulness"),
            avg_answer_relevancy=Avg("answer_relevancy"),
            avg_context_precision=Avg("context_precision"),
            avg_context_recall=Avg("context_recall"),
            total_evaluated=Count("id"),
        )
        return Response(success_response(data=metrics))


class QueryLogListView(APIView):
    """GET /api/v1/analytics/query-logs/ — Paginated query logs with search and filter."""
    permission_classes = [IsAdmin]

    def get(self, request):
        qs = QueryLog.objects.order_by("-created_at")

        # Filter by query_type
        query_type = request.query_params.get("query_type")
        if query_type:
            qs = qs.filter(query_type=query_type)

        # Keyword search
        search = request.query_params.get("search")
        if search:
            qs = qs.filter(query__icontains=search)

        # Failed only flag
        failed_only = request.query_params.get("failed_only")
        if failed_only == "1":
            qs = qs.filter(Q(faithfulness__lt=0.5) | Q(confidence_score=0))

        qs = qs[:200]
        data = [
            {
                "id": str(l.id),
                "query": l.query[:300],
                "query_type": l.query_type,
                "confidence_score": l.confidence_score,
                "faithfulness": l.faithfulness,
                "answer_relevancy": l.answer_relevancy,
                "context_precision": l.context_precision,
                "context_recall": l.context_recall,
                "latency_ms": l.latency_ms,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in qs
        ]
        return Response(success_response(data=data))

