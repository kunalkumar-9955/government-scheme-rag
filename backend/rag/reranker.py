"""
rag/reranker.py — Cross-encoder reranking using BAAI/bge-reranker-v2-m3 (local)
"""
import logging
from typing import Optional
from django.conf import settings
from .retriever import RetrievalResult

logger = logging.getLogger(__name__)

_reranker_model = None


def _get_reranker():
    """Lazy-load the reranker model (singleton)."""
    global _reranker_model
    if _reranker_model is None:
        model_name = settings.RERANKER_MODEL
        try:
            from FlagEmbedding import FlagReranker
            _reranker_model = FlagReranker(model_name, use_fp16=True)
            logger.info("Reranker loaded: %s", model_name)
        except ImportError:
            logger.warning("FlagEmbedding not available. Reranker disabled.")
            _reranker_model = None
    return _reranker_model


class Reranker:
    """
    Cross-encoder reranker that re-scores retrieved chunks
    against the original query for higher precision.
    Uses BAAI/bge-reranker-v2-m3 (local, free).
    """

    def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        top_k: int = None,
    ) -> list[RetrievalResult]:
        """
        Rerank retrieval results using cross-encoder.

        Args:
            query: Original user query
            results: Retrieved chunks from hybrid retrieval
            top_k: Number of top results to return after reranking

        Returns:
            Reranked list, sorted by cross-encoder score
        """
        if not results:
            return results

        top_k = top_k or settings.RAG_TOP_K_RERANK

        if not settings.USE_RERANKER:
            logger.info("Reranker disabled — returning top %d by RRF score", top_k)
            return results[:top_k]

        reranker = _get_reranker()
        if reranker is None:
            logger.warning("Reranker not available — returning top %d by RRF score", top_k)
            return results[:top_k]

        try:
            # Build query-passage pairs
            pairs = [[query, r.content] for r in results]

            # Compute cross-encoder scores
            scores = reranker.compute_score(pairs, normalize=True)
            if isinstance(scores, float):
                scores = [scores]

            # Attach reranker scores
            for result, score in zip(results, scores):
                result.score = float(score)

            # Sort by reranker score descending
            reranked = sorted(results, key=lambda r: r.score, reverse=True)
            logger.debug("Reranked %d → top %d (best score: %.4f)", len(results), top_k, reranked[0].score)

            return reranked[:top_k]

        except Exception as e:
            logger.error("Reranking failed: %s — using original order", e)
            return results[:top_k]
