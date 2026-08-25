"""apps/analytics/tasks.py — Celery tasks for RAG evaluation"""
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    queue="evaluation",
    name="apps.analytics.tasks.run_nightly_rag_evaluation",
)
def run_nightly_rag_evaluation(self):
    """
    Nightly task: Run RAGAS evaluation on sample of recent messages.
    Stores metrics in QueryLog table.
    """
    from apps.chat.models import Message, MessageRole
    from apps.analytics.models import QueryLog

    # Get recent assistant messages without evaluation
    messages = Message.objects.filter(
        role=MessageRole.ASSISTANT,
        query_log__isnull=True,
        cited_sources__isnull=False,
        confidence_score__isnull=False,
    ).exclude(content="").order_by("-created_at")[:50]

    logger.info("Running RAG evaluation on %d messages", messages.count())

    for message in messages:
        try:
            _evaluate_single_message(message)
        except Exception as e:
            logger.error("Evaluation failed for message %s: %s", message.id, e)

    logger.info("Nightly RAG evaluation complete")


def _evaluate_single_message(message):
    """Evaluate a single message using RAGAS metrics."""
    from apps.analytics.models import QueryLog
    from apps.chat.models import Message

    # Get the user query (previous user message)
    user_msg = Message.objects.filter(
        conversation=message.conversation,
        role="user",
        created_at__lt=message.created_at,
    ).order_by("-created_at").first()

    if not user_msg:
        return

    query = user_msg.content
    answer = message.content
    contexts = [c.get("snippet", "") for c in (message.cited_sources or [])]

    if not contexts:
        return

    try:
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
        from datasets import Dataset

        dataset = Dataset.from_dict({
            "question": [query],
            "answer": [answer],
            "contexts": [contexts],
            "ground_truth": [answer],  # Using answer as proxy ground truth
        })

        result = evaluate(dataset, metrics=[faithfulness, answer_relevancy, context_precision, context_recall])
        scores = result.to_pandas().iloc[0].to_dict()

        QueryLog.objects.create(
            message=message,
            query=query,
            query_type=message.query_type,
            retrieved_doc_ids=[c.get("document_id") for c in (message.cited_sources or [])],
            num_chunks_retrieved=len(message.cited_sources or []),
            confidence_score=message.confidence_score,
            latency_ms=message.latency_ms,
            faithfulness=scores.get("faithfulness"),
            answer_relevancy=scores.get("answer_relevancy"),
            context_precision=scores.get("context_precision"),
            context_recall=scores.get("context_recall"),
            evaluated_at=timezone.now(),
        )
    except Exception as e:
        QueryLog.objects.create(
            message=message,
            query=query,
            confidence_score=message.confidence_score,
            evaluation_error=str(e)[:500],
            evaluated_at=timezone.now(),
        )
        raise


@shared_task(
    queue="maintenance",
    name="apps.analytics.tasks.cleanup_old_logs",
)
def cleanup_old_logs():
    """Weekly: Delete query logs older than 90 days."""
    from datetime import timedelta
    from apps.analytics.models import QueryLog
    cutoff = timezone.now() - timedelta(days=90)
    deleted, _ = QueryLog.objects.filter(created_at__lt=cutoff).delete()
    logger.info("Cleaned up %d old query logs", deleted)
