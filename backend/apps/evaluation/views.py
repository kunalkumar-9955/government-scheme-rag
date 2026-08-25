"""
apps/evaluation/views.py — Admin REST API for the RAG Evaluation System

Endpoints:
  GET/POST  /api/v1/evaluation/datasets/
  GET       /api/v1/evaluation/datasets/<id>/
  GET/POST  /api/v1/evaluation/datasets/<id>/cases/
  DELETE    /api/v1/evaluation/datasets/<id>/cases/<case_id>/
  POST      /api/v1/evaluation/runs/            — Trigger a new run
  GET       /api/v1/evaluation/runs/            — List all runs
  GET       /api/v1/evaluation/runs/<id>/       — Run detail + per-case results
  GET       /api/v1/evaluation/runs/<id>/compare/<other_id>/  — Side-by-side comparison

Security: All endpoints are IsAdmin only.
"""
import logging
from django.utils import timezone
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListCreateAPIView, RetrieveAPIView

from core.permissions import IsAdmin
from core.utils import success_response
from core.pagination import StandardResultsPagination

from .models import (
    EvaluationDataset,
    EvaluationCase,
    EvaluationRun,
    EvaluationCaseResult,
    RunStatus,
)
from .serializers import (
    EvaluationDatasetSerializer,
    EvaluationCaseSerializer,
    EvaluationRunListSerializer,
    EvaluationRunDetailSerializer,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Dataset Endpoints
# ─────────────────────────────────────────────────────────────

class EvaluationDatasetListView(ListCreateAPIView):
    """GET/POST /api/v1/evaluation/datasets/"""
    permission_classes = [IsAdmin]
    serializer_class   = EvaluationDatasetSerializer
    pagination_class   = None

    def get_queryset(self):
        return EvaluationDataset.objects.prefetch_related("cases", "runs").order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def list(self, request, *args, **kwargs):
        qs   = self.get_queryset()
        data = self.get_serializer(qs, many=True).data
        return Response(success_response(data=list(data)))

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        self.perform_create(ser)
        return Response(success_response(data=ser.data, message="Dataset created."), status=status.HTTP_201_CREATED)


class EvaluationDatasetDetailView(RetrieveAPIView):
    """GET /api/v1/evaluation/datasets/<id>/"""
    permission_classes = [IsAdmin]
    serializer_class   = EvaluationDatasetSerializer
    queryset = EvaluationDataset.objects.prefetch_related("cases", "runs")
    lookup_field = "id"

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response(success_response(data=self.get_serializer(instance).data))


# ─────────────────────────────────────────────────────────────
# Case Endpoints
# ─────────────────────────────────────────────────────────────

class EvaluationCaseListView(APIView):
    """GET/POST /api/v1/evaluation/datasets/<dataset_id>/cases/"""
    permission_classes = [IsAdmin]

    def _get_dataset(self, dataset_id):
        try:
            return EvaluationDataset.objects.get(id=dataset_id)
        except EvaluationDataset.DoesNotExist:
            return None

    def get(self, request, dataset_id):
        dataset = self._get_dataset(dataset_id)
        if not dataset:
            return Response({"success": False, "error": {"code": "NOT_FOUND", "message": "Dataset not found"}}, status=404)
        cases = dataset.cases.all().order_by("category", "difficulty")
        return Response(success_response(data=EvaluationCaseSerializer(cases, many=True).data))

    def post(self, request, dataset_id):
        dataset = self._get_dataset(dataset_id)
        if not dataset:
            return Response({"success": False, "error": {"code": "NOT_FOUND", "message": "Dataset not found"}}, status=404)
        data = dict(request.data)
        data["dataset"] = str(dataset.id)
        ser = EvaluationCaseSerializer(data=data)
        ser.is_valid(raise_exception=True)
        case = ser.save()
        return Response(success_response(data=EvaluationCaseSerializer(case).data, message="Case added."), status=201)


class EvaluationCaseDeleteView(APIView):
    """DELETE /api/v1/evaluation/datasets/<dataset_id>/cases/<case_id>/"""
    permission_classes = [IsAdmin]

    def delete(self, request, dataset_id, case_id):
        try:
            case = EvaluationCase.objects.get(id=case_id, dataset_id=dataset_id)
        except EvaluationCase.DoesNotExist:
            return Response({"success": False, "error": {"code": "NOT_FOUND", "message": "Case not found"}}, status=404)
        case.delete()
        return Response(success_response(message="Case deleted."))


# ─────────────────────────────────────────────────────────────
# Run Endpoints
# ─────────────────────────────────────────────────────────────

class EvaluationRunListView(APIView):
    """GET/POST /api/v1/evaluation/runs/"""
    permission_classes = [IsAdmin]

    def get(self, request):
        runs = EvaluationRun.objects.select_related("dataset").order_by("-created_at")[:50]
        data = EvaluationRunListSerializer(runs, many=True).data
        return Response(success_response(data=list(data)))

    def post(self, request):
        """
        Trigger a new evaluation run.
        Required body: { "dataset_id": "uuid", "label": "optional label" }
        Optional:      { "top_k_retrieve": 20, "top_k_rerank": 5,
                         "use_reranker": false, "retrieval_strategy": "HYBRID" }
        """
        dataset_id = request.data.get("dataset_id")
        if not dataset_id:
            return Response({"success": False, "error": {"code": "MISSING", "message": "dataset_id is required"}}, status=400)

        try:
            dataset = EvaluationDataset.objects.get(id=dataset_id)
        except EvaluationDataset.DoesNotExist:
            return Response({"success": False, "error": {"code": "NOT_FOUND", "message": "Dataset not found"}}, status=404)

        if not dataset.cases.exists():
            return Response({"success": False, "error": {"code": "EMPTY_DATASET", "message": "Dataset has no evaluation cases."}}, status=400)

        # Build run config
        embedding_model    = request.data.get("embedding_model",    getattr(settings, "LLM_EMBEDDING_MODEL", "models/text-embedding-004"))
        chunk_size         = int(request.data.get("chunk_size",         getattr(settings, "RAG_CHUNK_SIZE", 512)))
        chunk_overlap      = int(request.data.get("chunk_overlap",      getattr(settings, "RAG_CHUNK_OVERLAP", 64)))
        top_k_retrieve     = int(request.data.get("top_k_retrieve",     getattr(settings, "RAG_TOP_K_RETRIEVE", 20)))
        top_k_rerank       = int(request.data.get("top_k_rerank",       getattr(settings, "RAG_TOP_K_RERANK", 5)))
        use_reranker       = bool(request.data.get("use_reranker",      getattr(settings, "USE_RERANKER", False)))
        retrieval_strategy = request.data.get("retrieval_strategy", "HYBRID")

        config_snapshot = {
            "embedding_model":    embedding_model,
            "chunk_size":         chunk_size,
            "chunk_overlap":      chunk_overlap,
            "top_k_retrieve":     top_k_retrieve,
            "top_k_rerank":       top_k_rerank,
            "use_reranker":       use_reranker,
            "retrieval_strategy": retrieval_strategy,
            "django_settings_module": getattr(settings, "DJANGO_SETTINGS_MODULE", ""),
        }

        run = EvaluationRun.objects.create(
            dataset            = dataset,
            label              = request.data.get("label", ""),
            embedding_model    = embedding_model,
            chunk_size         = chunk_size,
            chunk_overlap      = chunk_overlap,
            top_k_retrieve     = top_k_retrieve,
            top_k_rerank       = top_k_rerank,
            use_reranker       = use_reranker,
            retrieval_strategy = retrieval_strategy,
            config_snapshot    = config_snapshot,
            triggered_by       = request.user,
            status             = RunStatus.RUNNING,
            started_at         = timezone.now(),
            total_cases        = dataset.cases.count(),
        )

        # Execute synchronously (Celery-eager in phase 1; swap to .delay() in production)
        try:
            _execute_run(run)
        except Exception as exc:
            logger.exception("Evaluation run %s failed: %s", run.id, exc)
            run.status = RunStatus.FAILED
            run.error_message = str(exc)
            run.completed_at = timezone.now()
            run.save(update_fields=["status", "error_message", "completed_at"])

        run.refresh_from_db()
        return Response(
            success_response(data=EvaluationRunListSerializer(run).data, message=f"Run completed: {run.completed_cases}/{run.total_cases} cases."),
            status=201,
        )


def _execute_run(run: EvaluationRun):
    """
    Execute all evaluation cases for a run.
    Called synchronously in phase 1.
    """
    from rag.evaluator import RagEvaluator
    evaluator = RagEvaluator()
    cases = run.dataset.cases.all()
    case_result_dicts = []

    for case in cases:
        logger.info("Evaluating case %s for run %s", case.id, run.id)
        metrics = evaluator.evaluate_case(case, run)
        case_result_dicts.append(metrics)

        EvaluationCaseResult.objects.update_or_create(
            run=run,
            case=case,
            defaults={
                "retrieval_relevance":   metrics["retrieval_relevance"],
                "context_relevance":     metrics["context_relevance"],
                "answer_relevance":      metrics["answer_relevance"],
                "faithfulness":          metrics["faithfulness"],
                "citation_correctness":  metrics["citation_correctness"],
                "hallucination_score":   metrics["hallucination_score"],
                "retrieved_chunk_ids":   metrics["retrieved_chunk_ids"],
                "retrieved_document_ids":metrics["retrieved_document_ids"],
                "num_chunks_retrieved":  metrics["num_chunks_retrieved"],
                "actual_answer":         metrics["actual_answer"][:5000],
                "actual_citations":      metrics["actual_citations"],
                "faithfulness_breakdown":metrics["faithfulness_breakdown"],
                "error_message":         metrics["error_message"],
                "latency_ms":            metrics["latency_ms"],
            },
        )

    # Aggregate
    aggregates = evaluator.aggregate_run_metrics(case_result_dicts)
    run.avg_retrieval_relevance  = aggregates["retrieval_relevance"]
    run.avg_context_relevance    = aggregates["context_relevance"]
    run.avg_answer_relevance     = aggregates["answer_relevance"]
    run.avg_faithfulness         = aggregates["faithfulness"]
    run.avg_citation_correctness = aggregates["citation_correctness"]
    run.avg_hallucination_score  = aggregates["hallucination_score"]
    run.completed_cases          = len(case_result_dicts)
    run.status                   = RunStatus.COMPLETED
    run.completed_at             = timezone.now()
    run.save(update_fields=[
        "avg_retrieval_relevance", "avg_context_relevance", "avg_answer_relevance",
        "avg_faithfulness", "avg_citation_correctness", "avg_hallucination_score",
        "completed_cases", "status", "completed_at",
    ])
    logger.info("Evaluation run %s completed — %d cases.", run.id, run.completed_cases)


class EvaluationRunDetailView(APIView):
    """GET /api/v1/evaluation/runs/<run_id>/"""
    permission_classes = [IsAdmin]

    def get(self, request, run_id):
        try:
            run = EvaluationRun.objects.prefetch_related(
                "case_results", "case_results__case"
            ).get(id=run_id)
        except EvaluationRun.DoesNotExist:
            return Response({"success": False, "error": {"code": "NOT_FOUND", "message": "Run not found"}}, status=404)
        return Response(success_response(data=EvaluationRunDetailSerializer(run).data))


class EvaluationRunCompareView(APIView):
    """GET /api/v1/evaluation/runs/<run_id>/compare/<other_id>/"""
    permission_classes = [IsAdmin]

    METRIC_KEYS = [
        "avg_retrieval_relevance", "avg_context_relevance",
        "avg_answer_relevance",    "avg_faithfulness",
        "avg_citation_correctness","avg_hallucination_score",
    ]

    def get(self, request, run_id, other_id):
        try:
            run_a = EvaluationRun.objects.get(id=run_id)
            run_b = EvaluationRun.objects.get(id=other_id)
        except EvaluationRun.DoesNotExist:
            return Response({"success": False, "error": {"code": "NOT_FOUND", "message": "One or both runs not found"}}, status=404)

        def _format(run):
            return {
                "id":    str(run.id),
                "label": run.label or str(run.id)[:8],
                "status": run.status,
                "embedding_model":    run.embedding_model,
                "chunk_size":         run.chunk_size,
                "top_k_retrieve":     run.top_k_retrieve,
                "top_k_rerank":       run.top_k_rerank,
                "use_reranker":       run.use_reranker,
                "retrieval_strategy": run.retrieval_strategy,
                "total_cases":        run.total_cases,
                "completed_cases":    run.completed_cases,
                "duration_seconds":   run.duration_seconds,
                **{k: getattr(run, k) for k in self.METRIC_KEYS},
            }

        deltas = {}
        for k in self.METRIC_KEYS:
            a = getattr(run_a, k)
            b = getattr(run_b, k)
            if a is not None and b is not None:
                deltas[k] = round(b - a, 4)
            else:
                deltas[k] = None

        return Response(success_response(data={
            "run_a":  _format(run_a),
            "run_b":  _format(run_b),
            "deltas": deltas,
            "winner": {
                k: ("B" if (deltas[k] or 0) > 0 else "A" if (deltas[k] or 0) < 0 else "TIE")
                for k in self.METRIC_KEYS if k != "avg_hallucination_score"
            } | {
                "avg_hallucination_score": (
                    "B" if (deltas.get("avg_hallucination_score") or 0) < 0
                    else "A" if (deltas.get("avg_hallucination_score") or 0) > 0
                    else "TIE"
                )
            },
        }))
