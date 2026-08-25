"""
apps/evaluation/tests.py — Tests for the RAG Evaluation System
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.authentication.models import CustomUser
from apps.evaluation.models import (
    EvaluationDataset,
    EvaluationCase,
    EvaluationRun,
    EvaluationCaseResult,
    CaseDifficulty,
    CaseCategory,
    RunStatus,
)
from rag.evaluator import (
    _token_f1,
    _keyword_coverage,
    _sentence_has_support,
    RagEvaluator,
)


class EvaluatorMetricsUnitTests(TestCase):
    """Tests for deterministic token-level metric calculations in rag/evaluator.py."""

    def test_token_f1_exact_match(self):
        text = "Small and marginal farmers with cultivable landholding up to 2 hectares are eligible"
        f1 = _token_f1(text, text)
        self.assertAlmostEqual(f1, 1.0, places=3)

    def test_token_f1_partial_overlap(self):
        ref = "Farmers receive Rs 6000 per year in three equal installments"
        hyp = "Eligible farmers receive 6000 rupees in installments"
        f1 = _token_f1(hyp, ref)
        self.assertGreater(f1, 0.4)
        self.assertLessEqual(f1, 1.0)

    def test_token_f1_disjoint(self):
        ref = "Atal pension yojana guaranteed minimum monthly pension"
        hyp = "Solar rooftop subsidy scheme application portal"
        f1 = _token_f1(hyp, ref)
        self.assertEqual(f1, 0.0)

    def test_keyword_coverage_all_present(self):
        answer = "PM-KISAN provides Rs 6000 per year directly to the bank account of small farmers."
        keywords = ["6000", "bank account", "farmer"]
        cov = _keyword_coverage(answer, keywords)
        self.assertEqual(cov, 1.0)

    def test_keyword_coverage_partial(self):
        answer = "Eligible beneficiaries receive financial support in their bank account."
        keywords = ["6000", "bank account", "hectares"]
        cov = _keyword_coverage(answer, keywords)
        self.assertAlmostEqual(cov, 1 / 3, places=2)

    def test_sentence_has_support(self):
        chunks = [
            "Eligible farmers receive Rs 6,000 per year in three equal installments of Rs 2,000.",
            "e-KYC is mandatory for all PM-KISAN beneficiaries to continue receiving financial benefits.",
        ]
        supported_sent = "Farmers receive financial support in three installments."
        unsupported_sent = "The rocket was launched into outer space from Sriharikota yesterday."

        is_sup1, score1 = _sentence_has_support(supported_sent, chunks, threshold=0.15)
        is_sup2, score2 = _sentence_has_support(unsupported_sent, chunks, threshold=0.15)

        self.assertTrue(is_sup1)
        self.assertFalse(is_sup2)


class EvaluationAPITests(TestCase):
    """API endpoint integration tests."""

    def setUp(self):
        self.client = APIClient()
        self.admin = CustomUser.objects.create_superuser(
            email="eval_admin@test.gov.in",
            password="StrongPassword123!",
        )
        self.citizen = CustomUser.objects.create_user(
            email="eval_citizen@test.gov.in",
            password="CitizenPassword123!",
        )
        self.client.force_authenticate(user=self.admin)

        self.dataset = EvaluationDataset.objects.create(
            name="Test Scheme Benchmark",
            description="Testing evaluation benchmark",
            version="1.0",
        )
        self.case1 = EvaluationCase.objects.create(
            dataset=self.dataset,
            question="What is the benefit under PM-KISAN?",
            expected_evidence="Farmers receive 6000 per year",
            expected_answer_keywords=["6000", "farmers"],
            difficulty=CaseDifficulty.EASY,
            category=CaseCategory.BENEFITS,
        )

    def test_citizen_forbidden(self):
        """Citizens cannot access evaluation APIs."""
        self.client.force_authenticate(user=self.citizen)
        url = reverse("eval-dataset-list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_datasets(self):
        url = reverse("eval-dataset-list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["data"]), 1)
        self.assertEqual(res.data["data"][0]["name"], "Test Scheme Benchmark")

    def test_create_case(self):
        url = reverse("eval-case-list", kwargs={"dataset_id": self.dataset.id})
        payload = {
            "question": "What is the age limit for APY?",
            "expected_evidence": "18 to 40 years of age",
            "expected_answer_keywords": ["18", "40"],
            "difficulty": "EASY",
            "category": "ELIGIBILITY",
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.dataset.cases.count(), 2)

    def test_trigger_evaluation_run(self):
        url = reverse("eval-run-list")
        payload = {
            "dataset_id": str(self.dataset.id),
            "label": "Test Run Baseline",
            "top_k_retrieve": 10,
            "top_k_rerank": 3,
            "retrieval_strategy": "HYBRID",
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        run_id = res.data["data"]["id"]
        run = EvaluationRun.objects.get(id=run_id)
        self.assertEqual(run.status, RunStatus.COMPLETED)
        self.assertEqual(run.completed_cases, 1)
        self.assertIsNotNone(run.avg_faithfulness)
        self.assertIsNotNone(run.avg_hallucination_score)

    def test_compare_runs(self):
        # Create two runs
        run1 = EvaluationRun.objects.create(
            dataset=self.dataset,
            label="Run A (Top 5)",
            top_k_retrieve=5,
            status=RunStatus.COMPLETED,
            total_cases=1,
            completed_cases=1,
            avg_faithfulness=0.85,
            avg_retrieval_relevance=0.80,
            avg_context_relevance=0.75,
            avg_answer_relevance=0.90,
            avg_citation_correctness=1.0,
            avg_hallucination_score=0.15,
        )
        run2 = EvaluationRun.objects.create(
            dataset=self.dataset,
            label="Run B (Top 20 + Rerank)",
            top_k_retrieve=20,
            use_reranker=True,
            status=RunStatus.COMPLETED,
            total_cases=1,
            completed_cases=1,
            avg_faithfulness=0.95,
            avg_retrieval_relevance=0.90,
            avg_context_relevance=0.85,
            avg_answer_relevance=0.95,
            avg_citation_correctness=1.0,
            avg_hallucination_score=0.05,
        )

        url = reverse("eval-run-compare", kwargs={"run_id": run1.id, "other_id": run2.id})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        data = res.data["data"]
        self.assertEqual(data["deltas"]["avg_faithfulness"], 0.10)
        self.assertEqual(data["winner"]["avg_faithfulness"], "B")
        self.assertEqual(data["winner"]["avg_hallucination_score"], "B")
