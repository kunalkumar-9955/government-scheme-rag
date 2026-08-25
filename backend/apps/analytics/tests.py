"""
apps/analytics/tests.py — Unit & Integration Tests for RAG Evaluation & Analytics Dashboard.

Coverage:
1. Dashboard View (admin counts: users, conversations, messages, documents, latencies).
2. RAG Metrics View (faithfulness, answer relevancy, context precision, context recall).
3. Query Logs List View.
4. Role-based Permission Enforcement (Admin allowed, Citizen denied).
"""
import uuid
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.analytics.models import QueryLog
from apps.chat.models import Conversation, Message, MessageRole
from apps.documents.models import DocumentStatus, GovDocument
from apps.schemes.models import Ministry, SchemeCategory

User = get_user_model()


class TestAnalyticsEndpoints(TestCase):

    def setUp(self):
        self.client = APIClient()

        # Admin user
        self.admin = User.objects.create_user(
            email="admin@govscheme.ai",
            password="AdminPassword123!",
            role="ADMIN",
        )

        # Citizen user
        self.citizen = User.objects.create_user(
            email="citizen@govscheme.ai",
            password="CitizenPassword123!",
            role="USER",
        )

        # Create Category & Ministry
        self.cat = SchemeCategory.objects.create(name="Agriculture", slug="agriculture")
        self.ministry = Ministry.objects.create(name="Ministry of Agriculture", short_code="MoA")

        # Create Sample GovDocument
        self.doc = GovDocument.objects.create(
            title="PM-KISAN Operational Guidelines",
            category=self.cat,
            ministry=self.ministry,
            status=DocumentStatus.COMPLETED,
            file_name="guidelines.pdf",
            file_size_bytes=1048576,
            uploaded_by=self.admin,
        )

        # Create Sample Conversation & Messages
        self.conv = Conversation.objects.create(user=self.citizen, title="Eligibility Query")
        self.msg = Message.objects.create(
            conversation=self.conv,
            role=MessageRole.ASSISTANT,
            content="PM-KISAN provides income support of ₹6,000 per year.",
            query_type="eligibility",
            confidence_score=0.92,
            latency_ms=450,
        )

        # Create QueryLog with RAG Evaluation Metrics
        self.log = QueryLog.objects.create(
            message=self.msg,
            query="Am I eligible for PM-KISAN?",
            query_type="eligibility",
            num_chunks_retrieved=3,
            confidence_score=0.92,
            latency_ms=450,
            faithfulness=0.95,
            answer_relevancy=0.90,
            context_precision=0.88,
            context_recall=0.92,
            evaluated_at=timezone.now(),
        )

    def test_admin_dashboard_metrics(self):
        """GET /api/v1/analytics/dashboard/ — Admin access."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.get("/api/v1/analytics/dashboard/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()["data"]

        self.assertGreaterEqual(data["total_users"], 2)
        self.assertGreaterEqual(data["total_conversations"], 1)
        self.assertGreaterEqual(data["total_messages"], 1)
        self.assertGreaterEqual(data["total_documents"], 1)
        self.assertAlmostEqual(data["avg_confidence_score"], 0.92, places=2)
        self.assertEqual(data["avg_latency_ms"], 450)

    def test_rag_metrics_evaluation_view(self):
        """GET /api/v1/analytics/rag-metrics/ — RAGAS aggregate scores."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.get("/api/v1/analytics/rag-metrics/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()["data"]

        self.assertEqual(data["total_evaluated"], 1)
        self.assertAlmostEqual(data["avg_faithfulness"], 0.95, places=2)
        self.assertAlmostEqual(data["avg_answer_relevancy"], 0.90, places=2)
        self.assertAlmostEqual(data["avg_context_precision"], 0.88, places=2)
        self.assertAlmostEqual(data["avg_context_recall"], 0.92, places=2)

    def test_query_logs_list_view(self):
        """GET /api/v1/analytics/query-logs/ — Query history."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.get("/api/v1/analytics/query-logs/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()["data"]

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["query_type"], "eligibility")
        self.assertAlmostEqual(data[0]["faithfulness"], 0.95, places=2)

    def test_citizen_forbidden_access(self):
        """Citizens (role='USER') must be denied access to admin analytics."""
        self.client.force_authenticate(user=self.citizen)

        endpoints = [
            "/api/v1/analytics/dashboard/",
            "/api/v1/analytics/rag-metrics/",
            "/api/v1/analytics/query-logs/",
        ]
        for url in endpoints:
            res = self.client.get(url)
            self.assertEqual(
                res.status_code,
                status.HTTP_403_FORBIDDEN,
                f"Endpoint {url} should be forbidden for regular citizen",
            )
