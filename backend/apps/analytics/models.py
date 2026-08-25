"""apps/analytics/models.py — Query logs and RAG evaluation metrics"""
import uuid
from django.db import models


class QueryLog(models.Model):
    """Stores RAG query results with RAGAS evaluation metrics."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.OneToOneField(
        "chat.Message", on_delete=models.CASCADE, related_name="query_log", null=True, blank=True
    )
    query = models.TextField()
    query_type = models.CharField(max_length=20, blank=True)
    retrieved_doc_ids = models.JSONField(default=list)
    num_chunks_retrieved = models.IntegerField(default=0)
    confidence_score = models.FloatField(null=True, blank=True)
    latency_ms = models.IntegerField(null=True, blank=True)
    # RAGAS Metrics
    faithfulness = models.FloatField(null=True, blank=True)
    answer_relevancy = models.FloatField(null=True, blank=True)
    context_precision = models.FloatField(null=True, blank=True)
    context_recall = models.FloatField(null=True, blank=True)
    evaluation_error = models.TextField(blank=True)
    evaluated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "query_logs"
        ordering = ["-created_at"]
