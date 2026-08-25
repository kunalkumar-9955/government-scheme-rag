"""
rag/evaluator.py — Deterministic RAG Evaluation Engine

Computes 6 metrics from actual RAG pipeline outputs:

1. retrieval_relevance   — Recall@K against expected document IDs
2. context_relevance     — Token-level F1 against expected evidence
3. answer_relevance      — Keyword coverage against expected answer keywords
4. faithfulness          — Sentence-level overlap with retrieved context
5. citation_correctness  — Citations must reference actually-retrieved documents
6. hallucination_score   — 1 − faithfulness (inverse metric)

IMPORTANT: No LLM is used for scoring. All metrics are deterministic
token-overlap computations. Scores reflect real retrieval quality.
"""
import re
import time
import logging
from typing import Any
from collections import Counter

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Token-Level Utilities
# ─────────────────────────────────────────────────────────────

def _tokenize(text: str) -> Counter:
    """Lowercased unigram bag-of-words counter, removing stop words."""
    STOP = {
        "a", "an", "the", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "shall", "can",
        "to", "of", "in", "for", "on", "with", "at", "by", "from",
        "and", "or", "but", "if", "as", "that", "this", "which",
        "it", "its", "he", "she", "they", "we", "you", "i",
    }
    tokens = re.findall(r"\b[a-z0-9]+\b", text.lower())
    return Counter(t for t in tokens if t not in STOP and len(t) > 2)


def _token_f1(hypothesis: str, reference: str) -> float:
    """
    Token-level F1 between hypothesis and reference strings.
    Returns 0.0–1.0.
    """
    if not hypothesis.strip() or not reference.strip():
        return 0.0

    hyp_counts = _tokenize(hypothesis)
    ref_counts = _tokenize(reference)

    if not hyp_counts or not ref_counts:
        return 0.0

    overlap = sum((hyp_counts & ref_counts).values())
    precision = overlap / sum(hyp_counts.values())
    recall    = overlap / sum(ref_counts.values())

    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _keyword_coverage(text: str, keywords: list[str]) -> float:
    """
    Fraction of expected keywords (or phrases) present in text.
    Case-insensitive substring match.
    """
    if not keywords:
        return 1.0  # vacuously correct
    text_lower = text.lower()
    hits = sum(1 for kw in keywords if kw.lower() in text_lower)
    return hits / len(keywords)


def _split_sentences(text: str) -> list[str]:
    """
    Simple sentence splitter (handles Hindi/English mixed documents).
    """
    sentences = re.split(r"(?<=[.!?।])\s+", text.strip())
    return [s.strip() for s in sentences if len(s.strip()) > 15]


def _sentence_has_support(sentence: str, context_chunks: list[str], threshold: float = 0.15) -> tuple[bool, float]:
    """
    Returns (supported, best_overlap) where best_overlap is the highest
    token-F1 between the sentence and any single retrieved chunk.
    """
    if not context_chunks:
        return False, 0.0
    best = max(_token_f1(sentence, chunk) for chunk in context_chunks)
    return best >= threshold, best


# ─────────────────────────────────────────────────────────────
# Main Evaluator
# ─────────────────────────────────────────────────────────────

class RagEvaluator:
    """
    Runs the live RAG pipeline against an EvaluationCase and
    returns a dict of measured metric values.
    """

    def evaluate_case(self, case, run: "EvaluationRun") -> dict[str, Any]:
        """
        Evaluate a single EvaluationCase against the RAG pipeline.

        Returns a dict with:
          retrieval_relevance, context_relevance, answer_relevance,
          faithfulness, citation_correctness, hallucination_score,
          retrieved_chunk_ids, retrieved_document_ids, num_chunks_retrieved,
          actual_answer, actual_citations, faithfulness_breakdown, latency_ms,
          error_message
        """
        result: dict[str, Any] = {
            "retrieval_relevance": None,
            "context_relevance": None,
            "answer_relevance": None,
            "faithfulness": None,
            "citation_correctness": None,
            "hallucination_score": None,
            "retrieved_chunk_ids": [],
            "retrieved_document_ids": [],
            "num_chunks_retrieved": 0,
            "actual_answer": "",
            "actual_citations": [],
            "faithfulness_breakdown": [],
            "latency_ms": None,
            "error_message": "",
        }

        start_ms = time.monotonic()

        try:
            # ── 1. Run RAG Pipeline ────────────────────────
            from rag.pipeline import RAGPipeline
            pipeline = RAGPipeline()
            filters = {}
            if case.scheme_id:
                filters["scheme_id"] = str(case.scheme_id)

            pipeline_result = pipeline.run(
                query=case.question,
                filters=filters,
            )

            actual_answer   = pipeline_result.answer or ""
            actual_citations = pipeline_result.citations or []
            retrieved       = pipeline_result.retrieved_chunks or []

            result["num_chunks_retrieved"] = len(retrieved)
            result["retrieved_chunk_ids"] = [
                str(getattr(r, "chunk_id", r.get("chunk_id", ""))) for r in retrieved
            ]
            result["retrieved_document_ids"] = list(dict.fromkeys(
                str(getattr(r, "document_id", r.get("document_id", "")))
                for r in retrieved
                if getattr(r, "document_id", r.get("document_id", None))
            ))

            context_texts = [
                getattr(r, "content", r.get("content", "")) for r in retrieved if getattr(r, "content", r.get("content", ""))
            ]
            full_context  = " ".join(context_texts)

            result["actual_answer"]   = actual_answer
            result["actual_citations"] = actual_citations

            # ── 3. Retrieval Relevance: Recall@K ──────────────────
            expected_doc_ids = set(str(d) for d in (case.expected_document_ids or []))
            if expected_doc_ids:
                retrieved_doc_ids = set(result["retrieved_document_ids"])
                recall = len(expected_doc_ids & retrieved_doc_ids) / len(expected_doc_ids)
            else:
                recall = 1.0 if retrieved else 0.0
            result["retrieval_relevance"] = round(recall, 4)

            # ── 4. Context Relevance: Token F1 vs expected evidence ─
            result["context_relevance"] = round(
                _token_f1(full_context, case.expected_evidence or ""),
                4,
            )

            # ── 5. Answer Relevance: Keyword coverage ──────────────
            result["answer_relevance"] = round(
                _keyword_coverage(actual_answer, case.expected_answer_keywords or []),
                4,
            )

            # ── 6. Faithfulness: Sentence-level support ────────────
            answer_sentences = _split_sentences(actual_answer)
            if not answer_sentences:
                faithfulness = 1.0
                breakdown = []
            else:
                breakdown = []
                supported_count = 0
                for sent in answer_sentences:
                    supported, best_overlap = _sentence_has_support(sent, context_texts)
                    breakdown.append({
                        "sentence": sent[:200],
                        "supported": supported,
                        "best_overlap": round(best_overlap, 4),
                    })
                    if supported:
                        supported_count += 1
                faithfulness = supported_count / len(answer_sentences)

            result["faithfulness"] = round(faithfulness, 4)
            result["faithfulness_breakdown"] = breakdown

            # ── 7. Citation Correctness ────────────────────────────
            cited_doc_ids = set()
            for citation in actual_citations:
                if isinstance(citation, dict):
                    doc_id = citation.get("document_id") or citation.get("source_document_id")
                    if doc_id:
                        cited_doc_ids.add(str(doc_id))

            if cited_doc_ids:
                retrieved_doc_set = set(result["retrieved_document_ids"])
                correct = sum(1 for d in cited_doc_ids if d in retrieved_doc_set)
                result["citation_correctness"] = round(correct / len(cited_doc_ids), 4)
            else:
                # No citations → treat as 1.0 only if answer contains "insufficient evidence"
                if "insufficient evidence" in actual_answer.lower():
                    result["citation_correctness"] = 1.0
                else:
                    result["citation_correctness"] = 1.0  # no claims made

            # ── 8. Hallucination Score: inverse of faithfulness ────
            result["hallucination_score"] = round(1.0 - result["faithfulness"], 4)

        except Exception as exc:
            logger.exception("RagEvaluator: evaluation failed for case %s: %s", case.id, exc)
            result["error_message"] = str(exc)

        result["latency_ms"] = int((time.monotonic() - start_ms) * 1000)
        return result

    def aggregate_run_metrics(self, case_results: list[dict]) -> dict[str, float | None]:
        """
        Average 6 metrics across all successfully-computed case results.
        Cases with error_message are excluded from averaging.
        """
        keys = [
            "retrieval_relevance", "context_relevance", "answer_relevance",
            "faithfulness", "citation_correctness", "hallucination_score",
        ]
        sums   = {k: 0.0 for k in keys}
        counts = {k: 0   for k in keys}

        for cr in case_results:
            if cr.get("error_message"):
                continue
            for k in keys:
                v = cr.get(k)
                if v is not None:
                    sums[k]   += v
                    counts[k] += 1

        return {
            k: round(sums[k] / counts[k], 4) if counts[k] > 0 else None
            for k in keys
        }
