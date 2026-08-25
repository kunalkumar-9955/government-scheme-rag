"""
rag/pipeline.py - End-to-End RAG Pipeline Orchestrator.

Flow:
  User Query + Conversation History + Citizen Profile
      ↓ Query Understanding & Classification
      ↓ Query Transformation
      ↓ Embedding Generation
      ↓ Hybrid Retrieval
      ↓ Fallback Retrieval
      ↓ Cross-Encoder Reranking
      ↓ Deterministic Eligibility Evaluation
      ↓ Context Assembly + Citation Grounding
      ↓ LLM Generation
      ↓ Citation Annotation & Quality Scoring
"""

import logging
import time
from typing import Generator, List, Optional

from apps.eligibility.engine import EligibilityEngine
from apps.schemes.models import GovernmentScheme, SchemeStatus

from .embedder import EmbeddingService
from .retriever import HybridRetriever, RetrievalResult
from .reranker import Reranker
from .generator import LLMService
from .query_transformer import QueryTransformer
from .citation_builder import CitationBuilder


logger = logging.getLogger(__name__)


class RAGPipelineResult:
    """Structured outcome from the RAG Pipeline."""

    def __init__(
        self,
        answer: str,
        citations: list[dict],
        retrieved_chunks: list[dict],
        confidence_score: float,
        latency_ms: int,
        query_type: str,
        eligibility_result: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ):
        self.answer = answer
        self.citations = citations
        self.retrieved_chunks = retrieved_chunks
        self.confidence_score = confidence_score
        self.latency_ms = latency_ms
        self.query_type = query_type
        self.eligibility_result = eligibility_result
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        return {
            "answer": self.answer,
            "citations": self.citations,
            "retrieved_chunks": self.retrieved_chunks,
            "confidence_score": self.confidence_score,
            "latency_ms": self.latency_ms,
            "query_type": self.query_type,
            "eligibility_result": self.eligibility_result,
            "metadata": self.metadata,
        }


class RAGPipeline:
    """
    Main RAG orchestrator.

    Combines:
    - Query classification
    - Query transformation
    - Embeddings
    - Hybrid retrieval
    - Retrieval fallback
    - Reranking
    - Eligibility evaluation
    - Citation building
    - LLM generation
    """

    def __init__(self):
        self.embedder = EmbeddingService()
        self.retriever = HybridRetriever()
        self.reranker = Reranker()
        self.generator = LLMService()
        self.query_transformer = QueryTransformer()
        self.citation_builder = CitationBuilder()
        self.eligibility_engine = EligibilityEngine()

    # ============================================================
    # MAIN NON-STREAMING PIPELINE
    # ============================================================

    def run(
        self,
        query: str,
        user_profile: Optional[dict] = None,
        conversation_history: Optional[List[dict]] = None,
        filters: Optional[dict] = None,
    ) -> RAGPipelineResult:
        """
        Executes the complete synchronous RAG pipeline.
        """

        start_time = time.monotonic()

        # --------------------------------------------------------
        # 1. Query Understanding
        # --------------------------------------------------------

        query_type = self.query_transformer.classify(query)

        transformed = self.query_transformer.transform(
            query,
            query_type,
            user_profile,
        )

        primary_query = transformed.get(
            "primary_query",
            query,
        )

        hyde_text = transformed.get("hyde_text")

        logger.info(
            "Query classification: type=%s primary_query=%s",
            query_type,
            primary_query,
        )

        # --------------------------------------------------------
        # 2. Query Embedding
        # --------------------------------------------------------

        query_embedding = None

        try:
            query_embedding = self.embedder.embed_query(
                primary_query
            )
        except Exception as exc:
            logger.warning(
                "Query embedding failed: %s",
                exc,
            )

        # Optional HyDE embedding
        if hyde_text and query_embedding:
            try:
                hyde_embedding = self.embedder.embed_query(
                    hyde_text
                )

                if hyde_embedding:
                    query_embedding = [
                        (q + h) / 2
                        for q, h in zip(
                            query_embedding,
                            hyde_embedding,
                        )
                    ]

            except Exception as exc:
                logger.debug(
                    "HyDE embedding skipped: %s",
                    exc,
                )

        # --------------------------------------------------------
        # 3. Retrieval with Fallback
        # --------------------------------------------------------

        raw_results, retrieval_mode = self._retrieve_with_fallback(
            original_query=query,
            primary_query=primary_query,
            query_embedding=query_embedding,
            filters=filters,
        )

        logger.info(
            "Final retrieval result: mode=%s results=%d",
            retrieval_mode,
            len(raw_results),
        )

        # --------------------------------------------------------
        # 4. Eligibility Evaluation
        # --------------------------------------------------------

        eligibility_context, eligibility_data = (
            self._handle_eligibility(
                query,
                query_type,
                user_profile,
                raw_results,
            )
        )

        # --------------------------------------------------------
        # 5. No Context
        # --------------------------------------------------------

        if not raw_results and not eligibility_context:
            return self._no_context_response(
                query,
                query_type,
                start_time,
            )

        # --------------------------------------------------------
        # 6. Reranking
        # --------------------------------------------------------

        rerank_query = primary_query or query

        reranked_results = (
            self.reranker.rerank(
                rerank_query,
                raw_results,
            )
            if raw_results
            else []
        )

        # --------------------------------------------------------
        # 7. Context + Citations
        # --------------------------------------------------------

        context_block = (
            self.citation_builder.build_context_block(
                reranked_results
            )
        )

        citations = (
            self.citation_builder.build_citations(
                reranked_results
            )
        )

        # --------------------------------------------------------
        # 8. Answer Generation
        # --------------------------------------------------------

        # Eligibility is deterministic and has already been evaluated
        # by EligibilityEngine. Do NOT send the full retrieved scheme
        # document back through the LLM for eligibility queries.
        # This prevents the model from reproducing large chunks of
        # the source document in the final answer.
        if eligibility_context:
            answer = eligibility_context
        else:
            answer = self.generator.generate(
                user_query=query,
                context=context_block,
                conversation_history=conversation_history,
                user_profile=user_profile,
                query_type=query_type,
                eligibility_context=eligibility_context,
            )

        # --------------------------------------------------------
        # 9. Citation Annotation
        # --------------------------------------------------------

        annotated_answer = (
            self.citation_builder.annotate_response(
                answer,
                citations,
            )
        )

        # --------------------------------------------------------
        # 10. Confidence
        # --------------------------------------------------------

        confidence = self._compute_confidence(
            reranked_results,
            eligibility_data,
        )

        latency_ms = int(
            (time.monotonic() - start_time) * 1000
        )

        # --------------------------------------------------------
        # 11. Final Result
        # --------------------------------------------------------

        return RAGPipelineResult(
            answer=annotated_answer,
            citations=citations,
            retrieved_chunks=[
                r.to_dict()
                for r in raw_results
            ],
            confidence_score=confidence,
            latency_ms=latency_ms,
            query_type=query_type,
            eligibility_result=eligibility_data,
            metadata={
                "hyde_used": hyde_text is not None,
                "filters": filters,
                "retrieval_mode": retrieval_mode,
                "primary_query": primary_query,
                "original_query": query,
            },
        )

    # ============================================================
    # STREAMING PIPELINE
    # ============================================================

    def run_stream(
        self,
        query: str,
        user_profile: Optional[dict] = None,
        conversation_history: Optional[List[dict]] = None,
        filters: Optional[dict] = None,
    ) -> Generator[dict, None, None]:
        """
        Streaming RAG pipeline yielding SSE-compatible events.
        """

        start_time = time.monotonic()

        # --------------------------------------------------------
        # 1. Query Understanding
        # --------------------------------------------------------

        query_type = self.query_transformer.classify(query)

        transformed = self.query_transformer.transform(
            query,
            query_type,
            user_profile,
        )

        primary_query = transformed.get(
            "primary_query",
            query,
        )

        hyde_text = transformed.get("hyde_text")

        yield {
            "event": "status",
            "data": {
                "stage": "retrieving",
                "message": (
                    "Searching official government documents..."
                ),
            },
        }

        # --------------------------------------------------------
        # 2. Query Embedding
        # --------------------------------------------------------

        query_embedding = None

        try:
            query_embedding = self.embedder.embed_query(
                primary_query
            )
        except Exception as exc:
            logger.warning(
                "Streaming query embedding failed: %s",
                exc,
            )

        # Optional HyDE embedding
        if hyde_text and query_embedding:
            try:
                hyde_embedding = self.embedder.embed_query(
                    hyde_text
                )

                if hyde_embedding:
                    query_embedding = [
                        (q + h) / 2
                        for q, h in zip(
                            query_embedding,
                            hyde_embedding,
                        )
                    ]

            except Exception as exc:
                logger.debug(
                    "Streaming HyDE embedding skipped: %s",
                    exc,
                )

        # --------------------------------------------------------
        # 3. Retrieval with Fallback
        # --------------------------------------------------------

        raw_results, retrieval_mode = (
            self._retrieve_with_fallback(
                original_query=query,
                primary_query=primary_query,
                query_embedding=query_embedding,
                filters=filters,
            )
        )

        logger.info(
            "Streaming final retrieval: mode=%s results=%d",
            retrieval_mode,
            len(raw_results),
        )

        # --------------------------------------------------------
        # 4. Eligibility Evaluation
        # --------------------------------------------------------

        eligibility_context, eligibility_data = (
            self._handle_eligibility(
                query,
                query_type,
                user_profile,
                raw_results,
            )
        )

        # --------------------------------------------------------
        # 5. No Context
        # --------------------------------------------------------

        if not raw_results and not eligibility_context:

            yield {
                "event": "status",
                "data": {
                    "stage": "no_context",
                },
            }

            no_ctx_msg = (
                "I could not find official government scheme "
                "documents matching your query. "
                "Please rephrase or specify a scheme name."
            )

            yield {
                "event": "token",
                "data": {
                    "text": no_ctx_msg,
                },
            }

            yield {
                "event": "done",
                "data": {
                    "citations": [],
                    "confidence_score": 0.0,
                    "latency_ms": int(
                        (time.monotonic() - start_time) * 1000
                    ),
                    "query_type": query_type,
                    "full_answer": no_ctx_msg,
                    "eligibility_result": eligibility_data,
                },
            }

            return

        # --------------------------------------------------------
        # 6. Reranking
        # --------------------------------------------------------

        rerank_query = primary_query or query

        reranked_results = (
            self.reranker.rerank(
                rerank_query,
                raw_results,
            )
            if raw_results
            else []
        )

        # --------------------------------------------------------
        # 7. Context + Citations
        # --------------------------------------------------------

        context_block = (
            self.citation_builder.build_context_block(
                reranked_results
            )
        )

        citations = (
            self.citation_builder.build_citations(
                reranked_results
            )
        )

        # Send citations early
        yield {
            "event": "citations",
            "data": {
                "citations": citations,
            },
        }

        if eligibility_data:
            yield {
                "event": "eligibility",
                "data": eligibility_data,
            }

        yield {
            "event": "status",
            "data": {
                "stage": "generating",
                "message": (
                    "Generating grounded answer..."
                ),
            },
        }

        # --------------------------------------------------------
        # 8. Streaming Answer Generation
        # --------------------------------------------------------

        # Eligibility results are deterministic. The eligibility event
        # is already sent to the frontend above, so do not run the LLM
        # for this case. Running the LLM here would cause it to stream
        # the entire retrieved government document into the chat.
        if eligibility_context:
            full_answer = eligibility_context
        else:
            full_answer = ""

            for chunk in self.generator.generate_stream(
                user_query=query,
                context=context_block,
                conversation_history=conversation_history,
                user_profile=user_profile,
                query_type=query_type,
                eligibility_context=eligibility_context,
            ):

                full_answer += chunk

                yield {
                    "event": "token",
                    "data": {
                        "text": chunk,
                    },
                }

        # --------------------------------------------------------
        # 9. Citation Annotation
        # --------------------------------------------------------

        annotated_answer = (
            self.citation_builder.annotate_response(
                full_answer,
                citations,
            )
        )

        confidence = self._compute_confidence(
            reranked_results,
            eligibility_data,
        )

        latency_ms = int(
            (time.monotonic() - start_time) * 1000
        )

        # --------------------------------------------------------
        # 10. Done
        # --------------------------------------------------------

        yield {
            "event": "done",
            "data": {
                "citations": citations,
                "confidence_score": confidence,
                "latency_ms": latency_ms,
                "query_type": query_type,
                "full_answer": annotated_answer,
                "eligibility_result": eligibility_data,
                "retrieval_mode": retrieval_mode,
            },
        }

    # ============================================================
    # RETRIEVAL FALLBACK
    # ============================================================

    def _retrieve_with_fallback(
        self,
        original_query: str,
        primary_query: str,
        query_embedding: Optional[list[float]],
        filters: Optional[dict],
    ) -> tuple[list[RetrievalResult], str]:
        """
        Retrieves documents using multiple safe fallback levels.

        Order:

        1. Primary transformed query + embedding + filters
        2. Original user query + no embedding + filters
        3. Original user query + no filters
        4. Primary query + no filters

        This prevents a valid document from being rejected because
        query transformation, embedding, or optional filters were
        too restrictive.
        """

        # --------------------------------------------------------
        # Attempt 1
        # --------------------------------------------------------

        try:
            results = self.retriever.retrieve(
                primary_query,
                query_embedding,
                filters,
            )

            if results:
                logger.info(
                    "Retrieval successful on primary query."
                )

                return results, "primary"

        except Exception as exc:
            logger.warning(
                "Primary retrieval failed: %s",
                exc,
            )

        # --------------------------------------------------------
        # Attempt 2
        # --------------------------------------------------------

        if (
            original_query.strip()
            != primary_query.strip()
        ):

            try:
                results = self.retriever.retrieve(
                    original_query,
                    None,
                    filters,
                )

                if results:
                    logger.info(
                        "Retrieval successful using original query."
                    )

                    return results, "original_query"

            except Exception as exc:
                logger.warning(
                    "Original query retrieval failed: %s",
                    exc,
                )

        # --------------------------------------------------------
        # Attempt 3
        # --------------------------------------------------------

        if filters:

            try:
                results = self.retriever.retrieve(
                    original_query,
                    None,
                    None,
                )

                if results:
                    logger.info(
                        "Retrieval successful after removing filters."
                    )

                    return results, "original_query_no_filters"

            except Exception as exc:
                logger.warning(
                    "Unfiltered original query retrieval failed: %s",
                    exc,
                )

        # --------------------------------------------------------
        # Attempt 4
        # --------------------------------------------------------

        try:
            results = self.retriever.retrieve(
                primary_query,
                None,
                None,
            )

            if results:
                logger.info(
                    "Retrieval successful using primary query without filters."
                )

                return results, "primary_no_filters"

        except Exception as exc:
            logger.warning(
                "Final retrieval fallback failed: %s",
                exc,
            )

        # --------------------------------------------------------
        # Nothing found
        # --------------------------------------------------------

        logger.warning(
            "All retrieval attempts returned zero results. "
            "original=%s primary=%s",
            original_query,
            primary_query,
        )

        return [], "none"

    # ============================================================
    # ELIGIBILITY
    # ============================================================

    def _handle_eligibility(
        self,
        query: str,
        query_type: str,
        user_profile: Optional[dict],
        retrieved_results: List[RetrievalResult],
    ) -> tuple[Optional[str], Optional[dict]]:
        """
        Runs deterministic eligibility engine if the query
        involves eligibility or qualification.
        """

        query_lower = query.lower().strip()

        is_personal_eligibility_query = any(
            phrase in query_lower
            for phrase in [
                "am i eligible",
                "am i qualify",
                "do i qualify",
                "do i qualify for",
                "can i get",
                "can i apply",
                "can i avail",
                "can i receive",
                "will i get",
                "am i entitled",
                "my eligibility",
                "check my eligibility",
                "check eligibility for me",
            ]
        )

        if (
            query_type != "eligibility"
            and not is_personal_eligibility_query
        ):
            return None, None

        if not user_profile:
            return None, None

        candidate_schemes = self._find_candidate_schemes(
            query,
            retrieved_results,
        )

        if not candidate_schemes:
            return None, None

        evaluations = (
            self.eligibility_engine.evaluate_multiple_schemes(
                user_profile,
                candidate_schemes[:3],
            )
        )

        if not evaluations:
            return None, None

        context_lines = []
        eval_dicts = []

        for res in evaluations:

            eval_dict = res.to_dict()
            eval_dicts.append(eval_dict)

            # For an INSUFFICIENT_INFORMATION result, missing data is
            # not a failed rule. Keep the user-facing count accurate.
            if (
                res.verdict.value == "Insufficient Information"
                or str(res.verdict) == "Insufficient Information"
            ):
                display_failed_count = 0
            else:
                display_failed_count = len(res.failed_rules)

            context_lines.append(
                f"- **{res.scheme_name}**: "
                f"Verdict = **{res.verdict.value}** "
                f"(Confidence: {res.confidence_score:.2f})\n"
                f"  Explanation: "
                f"{res.summary_explanation}\n"
                f"  Passed Rules: "
                f"{len(res.passed_rules)} | "
                f"  Failed Rules: "
                f"{display_failed_count} | "
                f"  Missing Attributes: "
                f"{', '.join(res.missing_information) or 'None'}"
            )

        return (
            "\n\n".join(context_lines),
            {
                "evaluations": eval_dicts,
            },
        )

    # ============================================================
    # FIND CANDIDATE SCHEMES
    # ============================================================

    def _find_candidate_schemes(
        self,
        query: str,
        retrieved_results: List[RetrievalResult],
    ) -> List[GovernmentScheme]:
        """
        Identifies target GovernmentScheme objects from retrieved
        chunk metadata or query terms.
        """

        scheme_ids = set()

        for result in retrieved_results:

            if result.scheme_id:
                scheme_ids.add(result.scheme_id)

        # --------------------------------------------------------
        # Best case: retrieved chunks already identify scheme
        # --------------------------------------------------------

        if scheme_ids:

            return list(
                GovernmentScheme.objects.filter(
                    id__in=scheme_ids
                )
                .prefetch_related(
                    "eligibility_rules",
                    "sources",
                )
            )

        # --------------------------------------------------------
        # Fallback: search active schemes using query words
        # --------------------------------------------------------

        words = [
            word
            for word in query.split()
            if len(word) > 3
        ]

        if words:

            from django.db.models import Q

            q_obj = Q()

            for word in words[:5]:

                q_obj |= (
                    Q(name__icontains=word)
                    | Q(short_title__icontains=word)
                )

            return list(
                GovernmentScheme.objects.filter(
                    q_obj,
                    status=SchemeStatus.ACTIVE,
                )
                .prefetch_related(
                    "eligibility_rules",
                    "sources",
                )[:5]
            )

        return []

    # ============================================================
    # CONFIDENCE
    # ============================================================

    def _compute_confidence(
        self,
        results: List[RetrievalResult],
        eligibility_data: Optional[dict],
    ) -> float:
        """
        Computes response confidence score.
        """

        scores = []

        if results:

            result_scores = [
                r.score
                for r in results[:3]
                if r.score is not None
            ]

            scores.extend(result_scores)

        if (
            eligibility_data
            and "evaluations" in eligibility_data
        ):

            eval_scores = [
                e.get(
                    "confidence_score",
                    0.7,
                )
                for e in eligibility_data["evaluations"]
            ]

            if eval_scores:
                scores.append(
                    sum(eval_scores)
                    / len(eval_scores)
                )

        if not scores:
            return 0.5

        avg = sum(scores) / len(scores)

        return min(
            round(avg, 2),
            1.0,
        )

    # ============================================================
    # NO CONTEXT
    # ============================================================

    def _no_context_response(
        self,
        query: str,
        query_type: str,
        start_time: float,
    ) -> RAGPipelineResult:
        """
        Returns explicit non-hallucinating response when no
        official documents are available.
        """

        answer = (
            "Insufficient evidence: No official government "
            "scheme documents were found matching your query "
            "in the database.\n\n"
            "To prevent misinformation, the assistant generates "
            "answers only from verified government documentation.\n\n"
            "Please verify the scheme name, browse the Schemes "
            "directory, or consult the official government portals."
        )

        return RAGPipelineResult(
            answer=answer,
            citations=[],
            retrieved_chunks=[],
            confidence_score=0.0,
            latency_ms=int(
                (time.monotonic() - start_time) * 1000
            ),
            query_type=query_type,
            eligibility_result=None,
            metadata={
                "retrieval_mode": "none",
                "original_query": query,
            },
        )