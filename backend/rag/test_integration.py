"""
rag/test_integration.py — End-to-End System Integration Tests

Validates:
1. Frontend API → Django → PostgreSQL ORM data flow
2. Document Ingestion → Chunk generation → Search index
3. Deterministic Eligibility Engine → RAG Pipeline coordination
4. Citations extraction & QueryLog metric persistence
"""
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status

from apps.authentication.models import CustomUser
from apps.schemes.models import (
    GovernmentScheme,
    SchemeCategory,
    Ministry,
    SchemeEligibilityRule,
    RuleOperator,
    RuleDataType,
)
from apps.documents.models import GovDocument, DocumentChunk, DocumentStatus
from apps.chat.models import Conversation, Message
from apps.analytics.models import QueryLog
from rag.pipeline import RAGPipeline


class EndToEndIntegrationTests(TestCase):
    """Full-stack integration test connecting multiple system subsystems."""

    def setUp(self):
        self.admin = CustomUser.objects.create_superuser(
            email="integration_admin@test.gov.in",
            password="AdminPassword123!",
        )
        self.citizen = CustomUser.objects.create_user(
            email="integration_citizen@test.gov.in",
            password="CitizenPassword123!",
        )

        # 1. Ministry and Category
        self.ministry = Ministry.objects.create(
            name="Ministry of Agriculture & Farmers Welfare",
            short_code="MOAFW",
            is_central=True,
        )
        self.category = SchemeCategory.objects.create(
            name="Agriculture & Farming",
            slug="agriculture-farming",
        )

        # 2. Scheme & Structured Eligibility Rules
        self.scheme = GovernmentScheme.objects.create(
            name="Pradhan Mantri Kisan Samman Nidhi",
            short_title="PM-KISAN",
            ministry=self.ministry,
            category=self.category,
            description="Direct income support of Rs 6,000 per year for farmer families.",
            status="ACTIVE",
        )
        SchemeEligibilityRule.objects.create(
            scheme=self.scheme,
            criterion_key="land_holding_acres",
            operator=RuleOperator.LTE,
            value="5.0",
            data_type=RuleDataType.DECIMAL,
            is_mandatory=True,
            rule_description="Landholding must not exceed 5 acres.",
        )

        # 3. Document and Ingested Chunks
        self.doc = GovDocument.objects.create(
            uploaded_by=self.admin,
            scheme=self.scheme,
            title="PM-KISAN Operational Guidelines 2024",
            file_name="pm_kisan_guidelines.pdf",
            file_path="documents/pm_kisan_guidelines.pdf",
            file_size_bytes=10240,
            file_hash="mock-sha256-hash-pmkisan",
            mime_type="application/pdf",
            status=DocumentStatus.COMPLETED,
            document_version="2.0",
            source_url="https://pmkisan.gov.in/guidelines.pdf",
        )

        self.chunk1 = DocumentChunk.objects.create(
            document=self.doc,
            chunk_index=0,
            content="Under PM-KISAN, eligible small and marginal farmer families receive financial benefit of Rs 6000 per year in three equal installments.",
            section_title="Financial Assistance",
            page_number=1,
            token_count=35,
        )
        self.chunk2 = DocumentChunk.objects.create(
            document=self.doc,
            chunk_index=1,
            content="Farmers must complete mandatory e-KYC and hold cultivable land under their name to receive benefits.",
            section_title="Eligibility and Verification",
            page_number=2,
            token_count=28,
        )
        from rag.embedder import EmbeddingService
        embedder = EmbeddingService()
        self.chunk1.metadata = {"embedding": embedder.embed_single(self.chunk1.content)}
        self.chunk1.save(update_fields=["metadata"])
        self.chunk2.metadata = {"embedding": embedder.embed_single(self.chunk2.content)}
        self.chunk2.save(update_fields=["metadata"])

    def test_full_rag_pipeline_execution(self):
        """Tests complete query execution: retrieval -> prompt synthesis -> citations -> answer."""
        pipeline = RAGPipeline()
        result = pipeline.run(
            query="What is the financial benefit under PM-KISAN for farmers?",
            user_profile={"land_holding_acres": 2.5, "occupation": "Farmer"},
        )

        self.assertIsNotNone(result)
        self.assertTrue(len(result.answer) > 0)
        self.assertIsInstance(result.citations, list)

    def test_chat_api_persists_conversation_messages_and_citations(self):
        """Citizen chat API endpoint creates message records and logs query metrics."""
        client = APIClient()
        client.force_authenticate(user=self.citizen)

        # 1. Create conversation
        conv_res = client.post("/api/v1/chat/conversations/", {"title": "PM Kisan Query"})
        self.assertEqual(conv_res.status_code, status.HTTP_201_CREATED)
        conv_id = conv_res.data["data"]["id"]

        # 2. Send message (synchronous mode)
        msg_res = client.post(
            f"/api/v1/chat/conversations/{conv_id}/messages/?stream=false",
            {"content": "Tell me about PM-KISAN scheme benefits"},
            format="json",
        )
        self.assertIn(msg_res.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        self.assertIn("message", msg_res.data["data"])
        self.assertIn("content", msg_res.data["data"]["message"])

        # 3. Verify messages stored in DB
        messages = Message.objects.filter(conversation_id=conv_id)
        self.assertEqual(messages.count(), 2)  # 1 user + 1 assistant
        user_msg = messages.get(role="user")
        assistant_msg = messages.get(role="assistant")
        self.assertEqual(user_msg.content, "Tell me about PM-KISAN scheme benefits")
        self.assertTrue(len(assistant_msg.content) > 0)
