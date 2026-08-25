"""apps/evaluation/admin.py — Django admin registration for evaluation system."""
from django.contrib import admin
from .models import EvaluationDataset, EvaluationCase, EvaluationRun, EvaluationCaseResult


@admin.register(EvaluationDataset)
class EvaluationDatasetAdmin(admin.ModelAdmin):
    list_display  = ["name", "version", "is_active", "created_at"]
    search_fields = ["name"]
    list_filter   = ["is_active"]


@admin.register(EvaluationCase)
class EvaluationCaseAdmin(admin.ModelAdmin):
    list_display  = ["question_preview", "dataset", "category", "difficulty", "created_at"]
    list_filter   = ["dataset", "category", "difficulty"]
    search_fields = ["question"]

    def question_preview(self, obj):
        return obj.question[:80]
    question_preview.short_description = "Question"


@admin.register(EvaluationRun)
class EvaluationRunAdmin(admin.ModelAdmin):
    list_display = [
        "label_or_id", "dataset", "status", "total_cases", "completed_cases",
        "avg_faithfulness", "avg_retrieval_relevance", "avg_hallucination_score",
        "started_at",
    ]
    list_filter  = ["status", "retrieval_strategy", "use_reranker"]
    readonly_fields = [
        "id", "started_at", "completed_at", "avg_retrieval_relevance",
        "avg_context_relevance", "avg_answer_relevance", "avg_faithfulness",
        "avg_citation_correctness", "avg_hallucination_score",
        "config_snapshot",
    ]

    def label_or_id(self, obj):
        return obj.label or str(obj.id)[:8]
    label_or_id.short_description = "Run"


@admin.register(EvaluationCaseResult)
class EvaluationCaseResultAdmin(admin.ModelAdmin):
    list_display  = [
        "run", "question_preview", "retrieval_relevance", "faithfulness",
        "citation_correctness", "hallucination_score", "latency_ms",
    ]
    list_filter   = ["run"]
    readonly_fields = [
        "id", "faithfulness_breakdown", "retrieved_chunk_ids",
        "retrieved_document_ids", "actual_answer", "actual_citations",
    ]

    def question_preview(self, obj):
        return obj.case.question[:60]
    question_preview.short_description = "Question"
