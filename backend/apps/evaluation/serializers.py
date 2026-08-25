"""
apps/evaluation/serializers.py — REST serializers for evaluation system
"""
from rest_framework import serializers
from .models import (
    EvaluationDataset,
    EvaluationCase,
    EvaluationRun,
    EvaluationCaseResult,
)


class EvaluationCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model  = EvaluationCase
        fields = [
            "id", "dataset", "question",
            "expected_document_ids", "expected_evidence",
            "expected_answer_keywords", "scheme_id",
            "difficulty", "category", "notes", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class EvaluationDatasetSerializer(serializers.ModelSerializer):
    total_cases = serializers.SerializerMethodField()
    total_runs  = serializers.SerializerMethodField()

    class Meta:
        model  = EvaluationDataset
        fields = [
            "id", "name", "description", "version",
            "is_active", "total_cases", "total_runs",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_total_cases(self, obj):
        return obj.cases.count()

    def get_total_runs(self, obj):
        return obj.runs.count()


class EvaluationCaseResultSerializer(serializers.ModelSerializer):
    question   = serializers.CharField(source="case.question", read_only=True)
    difficulty = serializers.CharField(source="case.difficulty", read_only=True)
    category   = serializers.CharField(source="case.category",  read_only=True)

    class Meta:
        model  = EvaluationCaseResult
        fields = [
            "id", "case", "question", "difficulty", "category",
            "retrieval_relevance", "context_relevance", "answer_relevance",
            "faithfulness", "citation_correctness", "hallucination_score",
            "retrieved_chunk_ids", "retrieved_document_ids", "num_chunks_retrieved",
            "actual_answer", "actual_citations", "faithfulness_breakdown",
            "error_message", "latency_ms", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class EvaluationRunListSerializer(serializers.ModelSerializer):
    dataset_name = serializers.CharField(source="dataset.name", read_only=True)
    duration_seconds = serializers.SerializerMethodField()
    pass_rate = serializers.SerializerMethodField()

    class Meta:
        model  = EvaluationRun
        fields = [
            "id", "dataset", "dataset_name", "label", "status",
            "embedding_model", "chunk_size", "top_k_retrieve", "top_k_rerank",
            "use_reranker", "retrieval_strategy",
            "total_cases", "completed_cases",
            "avg_retrieval_relevance", "avg_context_relevance",
            "avg_answer_relevance", "avg_faithfulness",
            "avg_citation_correctness", "avg_hallucination_score",
            "duration_seconds", "pass_rate",
            "started_at", "completed_at", "created_at",
        ]
        read_only_fields = [
            "id", "status", "total_cases", "completed_cases",
            "avg_retrieval_relevance", "avg_context_relevance",
            "avg_answer_relevance", "avg_faithfulness",
            "avg_citation_correctness", "avg_hallucination_score",
            "started_at", "completed_at", "created_at",
        ]

    def get_duration_seconds(self, obj):
        return obj.duration_seconds

    def get_pass_rate(self, obj):
        """Fraction of cases with faithfulness >= 0.7."""
        if not obj.completed_cases:
            return None
        passing = obj.case_results.filter(faithfulness__gte=0.7).count()
        return round(passing / obj.completed_cases, 4)


class EvaluationRunDetailSerializer(EvaluationRunListSerializer):
    case_results = EvaluationCaseResultSerializer(many=True, read_only=True)
    config_snapshot = serializers.JSONField(read_only=True)

    class Meta(EvaluationRunListSerializer.Meta):
        fields = EvaluationRunListSerializer.Meta.fields + ["case_results", "config_snapshot", "error_message"]
