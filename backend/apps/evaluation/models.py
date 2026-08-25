"""
apps/evaluation/models.py — RAG Evaluation System

Stores:
  - EvaluationDataset: Named collections of curated Q&A test cases
  - EvaluationCase: Single test case (question + expected docs/evidence/keywords)
  - EvaluationRun: One complete evaluation pass with config snapshot
  - EvaluationCaseResult: Per-case measured metrics within a run

All metrics are deterministically computed from actual retrieval results.
No fabricated or LLM-generated scores are stored.
"""
import uuid
from django.db import models
from django.contrib.postgres.fields import ArrayField


# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────

class CaseDifficulty(models.TextChoices):
    EASY   = "EASY",   "Easy"
    MEDIUM = "MEDIUM", "Medium"
    HARD   = "HARD",   "Hard"


class CaseCategory(models.TextChoices):
    ELIGIBILITY  = "ELIGIBILITY",  "Eligibility Query"
    BENEFITS     = "BENEFITS",     "Benefits Query"
    PROCEDURE    = "PROCEDURE",    "Application Procedure"
    DOCUMENTS    = "DOCUMENTS",    "Required Documents"
    COMPARISON   = "COMPARISON",   "Scheme Comparison"
    GENERAL      = "GENERAL",      "General Information"


class RunStatus(models.TextChoices):
    PENDING    = "PENDING",    "Pending"
    RUNNING    = "RUNNING",    "Running"
    COMPLETED  = "COMPLETED",  "Completed"
    FAILED     = "FAILED",     "Failed"


class RetrievalStrategy(models.TextChoices):
    DENSE   = "DENSE",   "Dense Only (pgvector)"
    SPARSE  = "SPARSE",  "Sparse Only (Full-Text Search)"
    HYBRID  = "HYBRID",  "Hybrid (RRF Fusion)"


# ─────────────────────────────────────────────────────────────
# EvaluationDataset — named collection of test cases
# ─────────────────────────────────────────────────────────────

class EvaluationDataset(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name        = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    version     = models.CharField(max_length=20, default="1.0")
    is_active   = models.BooleanField(default=True)
    created_by  = models.ForeignKey(
        "authentication.CustomUser",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="evaluation_datasets",
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        app_label   = "evaluation"
        ordering    = ["-created_at"]
        verbose_name = "Evaluation Dataset"

    def __str__(self):
        return f"{self.name} v{self.version} ({self.cases.count()} cases)"


# ─────────────────────────────────────────────────────────────
# EvaluationCase — single Q&A test case
# ─────────────────────────────────────────────────────────────

class EvaluationCase(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dataset    = models.ForeignKey(
        EvaluationDataset,
        on_delete=models.CASCADE,
        related_name="cases",
    )

    # The question sent to the RAG pipeline
    question   = models.TextField()

    # UUIDs of GovDocument records that MUST appear in retrieved chunks
    # Stored as a JSON array so we don't need a cross-app M2M at migration time
    expected_document_ids = models.JSONField(
        default=list,
        help_text="List of GovDocument UUIDs that must be retrieved for this query.",
    )

    # Verbatim evidence passage that should appear in the retrieved context
    expected_evidence = models.TextField(
        help_text="Key passage or evidence sentence that the retrieval must surface.",
    )

    # Keywords/phrases that must appear in a correct answer
    expected_answer_keywords = models.JSONField(
        default=list,
        help_text="List of words/phrases that must appear in a correct answer.",
    )

    # Optional scheme restriction
    scheme_id = models.UUIDField(
        null=True, blank=True,
        help_text="If set, retrieval is filtered to this scheme's documents.",
    )

    difficulty = models.CharField(max_length=10, choices=CaseDifficulty.choices, default=CaseDifficulty.MEDIUM)
    category   = models.CharField(max_length=20, choices=CaseCategory.choices, default=CaseCategory.GENERAL)
    notes      = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "evaluation"
        ordering  = ["dataset", "category", "difficulty"]
        verbose_name = "Evaluation Case"

    def __str__(self):
        return f"[{self.category}][{self.difficulty}] {self.question[:80]}"


# ─────────────────────────────────────────────────────────────
# EvaluationRun — one complete evaluation pass
# ─────────────────────────────────────────────────────────────

class EvaluationRun(models.Model):
    id      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dataset = models.ForeignKey(
        EvaluationDataset,
        on_delete=models.CASCADE,
        related_name="runs",
    )
    label = models.CharField(
        max_length=200, blank=True,
        help_text="Human-readable label for this run e.g. 'Baseline hybrid top-20'.",
    )
    status = models.CharField(max_length=20, choices=RunStatus.choices, default=RunStatus.PENDING)

    # ── Configuration fingerprint ────────────────────────────
    embedding_model     = models.CharField(max_length=100, default="models/text-embedding-004")
    chunk_size          = models.IntegerField(default=512)
    chunk_overlap       = models.IntegerField(default=64)
    top_k_retrieve      = models.IntegerField(default=20)
    top_k_rerank        = models.IntegerField(default=5)
    use_reranker        = models.BooleanField(default=False)
    retrieval_strategy  = models.CharField(
        max_length=10,
        choices=RetrievalStrategy.choices,
        default=RetrievalStrategy.HYBRID,
    )
    config_snapshot     = models.JSONField(default=dict)  # full settings dict at run time

    # ── Timing ───────────────────────────────────────────────
    started_at   = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    # ── Aggregate Metrics (averaged across all cases) ────────
    total_cases              = models.IntegerField(default=0)
    completed_cases          = models.IntegerField(default=0)
    avg_retrieval_relevance  = models.FloatField(null=True, blank=True)
    avg_context_relevance    = models.FloatField(null=True, blank=True)
    avg_answer_relevance     = models.FloatField(null=True, blank=True)
    avg_faithfulness         = models.FloatField(null=True, blank=True)
    avg_citation_correctness = models.FloatField(null=True, blank=True)
    avg_hallucination_score  = models.FloatField(null=True, blank=True)

    triggered_by = models.ForeignKey(
        "authentication.CustomUser",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="evaluation_runs",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "evaluation"
        ordering  = ["-created_at"]
        verbose_name = "Evaluation Run"

    def __str__(self):
        return f"Run {self.label or str(self.id)[:8]} [{self.status}] — {self.dataset.name}"

    @property
    def duration_seconds(self):
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


# ─────────────────────────────────────────────────────────────
# EvaluationCaseResult — per-case measured metrics
# ─────────────────────────────────────────────────────────────

class EvaluationCaseResult(models.Model):
    id   = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run  = models.ForeignKey(
        EvaluationRun,
        on_delete=models.CASCADE,
        related_name="case_results",
    )
    case = models.ForeignKey(
        EvaluationCase,
        on_delete=models.CASCADE,
        related_name="results",
    )

    # ── Measured Metrics (0.0–1.0) ───────────────────────────
    retrieval_relevance  = models.FloatField(null=True, blank=True,
        help_text="Recall@K: fraction of expected_document_ids found in retrieved set.")
    context_relevance    = models.FloatField(null=True, blank=True,
        help_text="Token-level F1 between retrieved context and expected_evidence.")
    answer_relevance     = models.FloatField(null=True, blank=True,
        help_text="Keyword coverage: fraction of expected_answer_keywords in actual answer.")
    faithfulness         = models.FloatField(null=True, blank=True,
        help_text="Fraction of answer sentences with ≥1 supporting retrieved chunk.")
    citation_correctness = models.FloatField(null=True, blank=True,
        help_text="Fraction of cited documents that were actually retrieved.")
    hallucination_score  = models.FloatField(null=True, blank=True,
        help_text="1 − faithfulness. Lower is better.")

    # ── Retrieval provenance ─────────────────────────────────
    retrieved_chunk_ids    = models.JSONField(default=list)
    retrieved_document_ids = models.JSONField(default=list)
    num_chunks_retrieved   = models.IntegerField(default=0)

    # ── Answer & Citation snapshots ──────────────────────────
    actual_answer       = models.TextField(blank=True)
    actual_citations    = models.JSONField(default=list)
    faithfulness_breakdown = models.JSONField(
        default=list,
        help_text="List of {sentence, supported: bool, best_overlap: float} per answer sentence.",
    )

    # ── Error tracking ───────────────────────────────────────
    error_message = models.TextField(blank=True)
    latency_ms    = models.IntegerField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label    = "evaluation"
        ordering     = ["run", "case"]
        unique_together = [["run", "case"]]
        verbose_name = "Evaluation Case Result"

    def __str__(self):
        return f"Result[{self.run_id}][{self.case_id}] faith={self.faithfulness:.2f}" if self.faithfulness else f"Result[{self.run_id}][{self.case_id}]"
