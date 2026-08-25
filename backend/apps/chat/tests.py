"""
apps/chat/tests.py — Comprehensive Unit & Integration Tests for RAG AI Chatbot.

Coverage:
1. Query Understanding & Classification across all 9 intent types.
2. RAG Pipeline sync & streaming execution with profile context.
3. Grounded answer generation and citation annotation.
4. Deterministic eligibility engine integration within RAG flow.
5. Conversation lifecycle: Create, List, Detail, and Delete.
6. Message streaming (SSE) and synchronous JSON message delivery.
7. Message feedback & quality rating.
8. Access control & security isolation across users.
"""
from decimal import Decimal
import json
import uuid
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.chat.models import Conversation, Message, MessageFeedback, MessageRole
from apps.schemes.models import (
    GovernmentScheme,
    Ministry,
    RuleDataType,
    RuleOperator,
    SchemeCategory,
    SchemeEligibilityRule,
    SchemeSource,
    SchemeStatus,
    SourceType,
    State,
)
from apps.users.models import OccupationCategory, SocialCategory, UserProfile
from rag.citation_builder import CitationBuilder
from rag.generator import LLMService
from rag.pipeline import RAGPipeline
from rag.query_transformer import QueryTransformer
from rag.retriever import RetrievalResult

User = get_user_model()


# ─────────────────────────────────────────────────────────────
# 1. Query Understanding & 9 Intent Categories Tests
# ─────────────────────────────────────────────────────────────

class TestQueryUnderstanding(TestCase):

    def setUp(self):
        self.transformer = QueryTransformer()

    def test_intent_classification_all_nine_categories(self):
        cases = [
            ("Am I eligible for PM-KISAN scheme?", "eligibility"),
            ("Do I qualify for Ayushman Bharat?", "eligibility"),
            ("What schemes are available for farmers in Bihar?", "discovery"),
            ("Find education scholarships for students", "discovery"),
            ("What are the benefits and financial assistance provided?", "benefits"),
            ("How much money will I get under PMAY?", "benefits"),
            ("What documents are required to apply for ration card?", "documents"),
            ("Is Aadhaar card needed?", "documents"),
            ("How to apply online on the government portal?", "procedure"),
            ("What is the application process and registration steps?", "procedure"),
            ("Compare PM-KISAN vs State farmer scheme", "comparison"),
            ("What is the difference between scheme A and scheme B?", "comparison"),
            ("Explain clause 4.2 of the scheme guidelines", "document_explanation"),
            ("What does this section in the document mean?", "document_explanation"),
            ("What about my daughter?", "follow_up"),
            ("Can they also apply?", "follow_up"),
            ("Tell me about the National Health Mission", "general"),
        ]
        for query, expected_intent in cases:
            classified = self.transformer.classify(query)
            self.assertEqual(
                classified,
                expected_intent,
                f"Query '{query}' classified as '{classified}', expected '{expected_intent}'",
            )

    def test_profile_context_injection(self):
        user_ctx = {
            "state": "Bihar",
            "occupation": "STUDENT",
            "age": 22,
            "annual_income_inr": 150000,
        }
        res = self.transformer.transform("What scholarships can I get?", "discovery", user_ctx)
        self.assertIn("Citizen Context", res["primary_query"])
        self.assertIn("Bihar", res["primary_query"])
        self.assertIn("STUDENT", res["primary_query"])


# ─────────────────────────────────────────────────────────────
# 2. Citation Builder Tests
# ─────────────────────────────────────────────────────────────

class TestCitationBuilder(TestCase):

    def setUp(self):
        self.builder = CitationBuilder()

    def test_build_citations_and_context_block(self):
        mock_chunks = [
            RetrievalResult(
                chunk_id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content="PM-KISAN provides Rs 6000 per year to small and marginal farmers in 3 installments.",
                score=0.92,
                metadata={},
                page_number=2,
                section_title="Financial Benefits",
                document_title="PM-KISAN Operational Guidelines",
                ministry="Ministry of Agriculture",
            )
        ]

        citations = self.builder.build_citations(mock_chunks)
        self.assertEqual(len(citations), 1)
        self.assertEqual(citations[0]["citation_number"], 1)
        self.assertEqual(citations[0]["document_title"], "PM-KISAN Operational Guidelines")

        context_block = self.builder.build_context_block(mock_chunks)
        self.assertIn("[Source 1: PM-KISAN Operational Guidelines", context_block)
        self.assertIn("Page 2", context_block)

    def test_citation_contains_all_six_required_fields(self):
        """
        Verify citation contains all required fields:
        - Scheme name
        - Document name
        - Page number
        - Section
        - Source URL
        - Document version
        """
        mock_chunks = [
            RetrievalResult(
                chunk_id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                content="Assistance of ₹6,000 per year.",
                score=0.88,
                metadata={"version": "2.1"},
                page_number=7,
                section_title="Eligibility Section",
                document_title="PM-KISAN Guidelines 2024",
                source_url="https://pmkisan.gov.in/guidelines.pdf",
                scheme_name="PM-KISAN",
                document_version="2.1",
            )
        ]
        citations = self.builder.build_citations(mock_chunks)
        self.assertEqual(len(citations), 1)
        cite = citations[0]

        self.assertEqual(cite["scheme_name"], "PM-KISAN")
        self.assertEqual(cite["document_name"], "PM-KISAN Guidelines 2024")
        self.assertEqual(cite["page_number"], 7)
        self.assertEqual(cite["section"], "Eligibility Section")
        self.assertEqual(cite["source_url"], "https://pmkisan.gov.in/guidelines.pdf")
        self.assertEqual(cite["document_version"], "2.1")

    def test_citation_validation_strips_hallucinated_sources(self):
        """
        Validator must strip or sanitize hallucinated citation markers not present in retrieved set.
        """
        retrieved_citations = [
            {"citation_number": 1, "document_title": "Doc 1", "scheme_name": "Scheme 1"},
            {"citation_number": 2, "document_title": "Doc 2", "scheme_name": "Scheme 2"},
        ]
        # LLM text mentions valid [Source 1] and hallucinated [Source 8] and [Source 99]
        llm_response = "Farmers receive assistance [Source 1]. Another benefit is free seeds [Source 8] and loans [Source 99]."
        cleaned_text, active_cites = self.builder.validate_and_filter_citations(llm_response, retrieved_citations)

        self.assertIn("[Source 1]", cleaned_text)
        self.assertNotIn("[Source 8]", cleaned_text)
        self.assertNotIn("[Source 99]", cleaned_text)
        self.assertEqual(len(active_cites), 1)
        self.assertEqual(active_cites[0]["citation_number"], 1)

    def test_annotate_response_appends_sources_if_missing(self):
        citations = [
            {
                "citation_number": 1,
                "scheme_name": "PMAY-G",
                "document_name": "Guidelines PDF",
                "ministry": "Ministry of Rural Dev",
                "page_number": 3,
                "section": "Financial Assistance",
                "document_version": "1.0",
                "source_url": "https://pmayg.nic.in",
            }
        ]
        raw_text = "The financial grant is Rs 1,20,000 for house construction."
        annotated = self.builder.annotate_response(raw_text, citations)
        self.assertIn("Official Sources & Evidence Grounding", annotated)
        self.assertIn("[1] PMAY-G", annotated)
        self.assertIn("Page 3", annotated)


# ─────────────────────────────────────────────────────────────
# 3. RAG Pipeline Execution Tests
# ─────────────────────────────────────────────────────────────

class TestRAGPipeline(TestCase):

    def setUp(self):
        self.pipeline = RAGPipeline()

        # Create Scheme & Rules
        self.cat = SchemeCategory.objects.create(name="Agriculture", slug="agriculture")
        self.ministry = Ministry.objects.create(name="Ministry of Agriculture", short_code="MoA")
        self.bihar = State.objects.create(name="Bihar", code="BR", is_union_territory=False)

        self.scheme = GovernmentScheme.objects.create(
            name="Pradhan Mantri Kisan Samman Nidhi",
            short_title="PM-KISAN",
            slug="pm-kisan",
            description="Income support scheme for all landholding farmer families.",
            category=self.cat,
            ministry=self.ministry,
            status=SchemeStatus.ACTIVE,
            official_source_url="https://pmkisan.gov.in",
        )

        SchemeEligibilityRule.objects.create(
            scheme=self.scheme,
            rule_group=1,
            criterion_key="occupation",
            operator=RuleOperator.EQUALS,
            value="FARMER",
            data_type=RuleDataType.STRING,
            is_mandatory=True,
            rule_description="Applicant must be a farmer",
        )

    def test_synchronous_rag_pipeline_run(self):
        user_profile = {
            "state": "Bihar",
            "occupation": "FARMER",
            "age": 35,
        }
        result = self.pipeline.run(
            query="Am I eligible for PM-KISAN scheme?",
            user_profile=user_profile,
        )
        self.assertIsNotNone(result.answer)
        self.assertIsInstance(result.citations, list)
        self.assertGreaterEqual(result.confidence_score, 0.0)
        self.assertEqual(result.query_type, "eligibility")
        # Check that eligibility engine was evaluated
        if result.eligibility_result:
            self.assertIn("evaluations", result.eligibility_result)

    def test_streaming_rag_pipeline_run(self):
        user_profile = {
            "state": "Bihar",
            "occupation": "FARMER",
        }
        events = list(
            self.pipeline.run_stream(
                query="What are the benefits of PM-KISAN?",
                user_profile=user_profile,
            )
        )
        event_types = [e.get("event") for e in events]
        self.assertIn("status", event_types)
        self.assertIn("done", event_types)

    def test_no_context_graceful_fallback(self):
        result = self.pipeline.run(query="Tell me about completely nonexistent fictional xyz scheme")
        self.assertIsNotNone(result.answer)
        self.assertIn("insufficient evidence", result.answer.lower())


# ─────────────────────────────────────────────────────────────
# 4. Chat Endpoints API Integration Tests
# ─────────────────────────────────────────────────────────────

class TestChatAPIEndpoints(TestCase):

    def setUp(self):
        self.client = APIClient()

        # Create Citizen User and Profile
        self.user = User.objects.create_user(
            email="citizen_chat@govscheme.ai",
            password="StrongPassword123!",
            role="USER",
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            full_name="Kavita Sharma",
            state="BR",
            district="Gaya",
            occupation=OccupationCategory.FARMER,
            social_category=SocialCategory.GENERAL,
            annual_income=Decimal("120000"),
        )

        # Create Second Citizen User for isolation checks
        self.other_user = User.objects.create_user(
            email="other_user@govscheme.ai",
            password="StrongPassword123!",
            role="USER",
        )

    def test_create_and_list_conversations(self):
        self.client.force_authenticate(user=self.user)

        # POST /api/v1/chat/conversations/
        res = self.client.post("/api/v1/chat/conversations/", {"title": "Farmer Support"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        conv_id = res.json()["data"]["id"]

        # GET /api/v1/chat/conversations/
        list_res = self.client.get("/api/v1/chat/conversations/")
        self.assertEqual(list_res.status_code, status.HTTP_200_OK)
        conversations = list_res.json()["data"]
        self.assertEqual(len(conversations), 1)
        self.assertEqual(conversations[0]["id"], conv_id)

    def test_conversation_detail_and_delete(self):
        self.client.force_authenticate(user=self.user)

        conv = Conversation.objects.create(user=self.user, title="Detail Check")
        res = self.client.get(f"/api/v1/chat/conversations/{conv.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json()["data"]["id"], str(conv.id))

        del_res = self.client.delete(f"/api/v1/chat/conversations/{conv.id}/")
        self.assertEqual(del_res.status_code, status.HTTP_200_OK)
        self.assertFalse(Conversation.objects.filter(id=conv.id).exists())

    def test_send_message_sync_mode(self):
        """POST /api/v1/chat/conversations/{id}/messages/?stream=false"""
        self.client.force_authenticate(user=self.user)
        conv = Conversation.objects.create(user=self.user, title="PM-KISAN Query")

        payload = {"content": "What benefits are provided under PM-KISAN?"}
        res = self.client.post(
            f"/api/v1/chat/conversations/{conv.id}/messages/?stream=false",
            payload,
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.json()["data"]
        self.assertIn("message", data)
        self.assertEqual(data["message"]["role"], "assistant")
        self.assertGreater(len(data["message"]["content"]), 0)

        # Check DB messages
        messages = Message.objects.filter(conversation=conv).order_by("created_at")
        self.assertEqual(messages.count(), 2)
        self.assertEqual(messages[0].role, MessageRole.USER)
        self.assertEqual(messages[1].role, MessageRole.ASSISTANT)

    def test_send_message_sse_streaming_mode(self):
        """POST /api/v1/chat/conversations/{id}/messages/ (SSE stream)"""
        self.client.force_authenticate(user=self.user)
        conv = Conversation.objects.create(user=self.user, title="Streaming Test")

        payload = {"content": "Am I eligible for farmer subsidies in Bihar?"}
        res = self.client.post(
            f"/api/v1/chat/conversations/{conv.id}/messages/",
            payload,
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res["Content-Type"], "text/event-stream")

    def test_message_feedback_submission(self):
        self.client.force_authenticate(user=self.user)
        conv = Conversation.objects.create(user=self.user)
        msg = Message.objects.create(
            conversation=conv,
            role=MessageRole.ASSISTANT,
            content="Official scheme details here.",
        )

        feedback_payload = {
            "rating": 5,
            "feedback_type": "HELPFUL",
            "comment": "Very clear and helpful breakdown!",
        }
        res = self.client.post(
            f"/api/v1/chat/messages/{msg.id}/feedback/",
            feedback_payload,
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        msg.refresh_from_db()
        self.assertEqual(msg.feedback_rating, 5)

        # Duplicate rating check
        res_dup = self.client.post(
            f"/api/v1/chat/messages/{msg.id}/feedback/",
            feedback_payload,
            format="json",
        )
        self.assertEqual(res_dup.status_code, status.HTTP_409_CONFLICT)

    def test_user_data_isolation(self):
        """User A must not access User B's conversations."""
        conv_user_a = Conversation.objects.create(user=self.user, title="User A Private")

        # Authenticate as User B
        self.client.force_authenticate(user=self.other_user)
        res = self.client.get(f"/api/v1/chat/conversations/{conv_user_a.id}/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

        # User B cannot send messages to User A's conversation
        res_msg = self.client.post(
            f"/api/v1/chat/conversations/{conv_user_a.id}/messages/?stream=false",
            {"content": "Unauthorized attempt"},
            format="json",
        )
        self.assertEqual(res_msg.status_code, status.HTTP_404_NOT_FOUND)
