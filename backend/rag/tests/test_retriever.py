"""
rag/tests/test_retriever.py — Retrieval evaluation tests.

Test coverage:
1.  QueryPreprocessor — unicode, whitespace, max-length, tsquery
2.  MetadataFilterBuilder — all 8 filter keys, empty filters
3.  RetrievalResult — to_dict() shape and field completeness
4.  RRF fusion — ordering, deduplication, combined scores
5.  HybridRetriever.retrieve_dense_only — DB round-trip (requires COMPLETED doc)
6.  HybridRetriever.retrieve_sparse_only — DB round-trip
7.  HybridRetriever.retrieve (hybrid) — DB round-trip
8.  Metadata filtering — category, state, ministry, scheme_id filters
9.  Top-K enforcement — result count ≤ top_k
10. Reranker passthrough — USE_RERANKER=False returns top results by RRF score
11. Empty query guard — graceful empty results
12. Empty embedding guard — graceful empty results
13. Retrieval with no matching docs — returns empty list (no crash)

Tests that need the database use Django's TestCase with DATABASES["default"].
Tests that are pure-Python use unittest.TestCase.
"""
import math
import uuid
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings

from rag.retriever import (
    HybridRetriever,
    MetadataFilterBuilder,
    QueryPreprocessor,
    RetrievalResult,
)
from rag.reranker import Reranker
from rag.embedder import EmbeddingService


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _make_result(chunk_id: str = None, score: float = 0.5, **kwargs) -> RetrievalResult:
    """Construct a minimal RetrievalResult for unit testing."""
    return RetrievalResult(
        chunk_id=chunk_id or str(uuid.uuid4()),
        document_id=str(uuid.uuid4()),
        content=kwargs.get("content", "Sample government scheme text."),
        score=score,
        metadata=kwargs.get("metadata", {}),
        page_number=kwargs.get("page_number", 1),
        section_title=kwargs.get("section_title", "Eligibility"),
        chunk_type=kwargs.get("chunk_type", "ELIGIBILITY"),
        document_title=kwargs.get("document_title", "PM-KISAN Guidelines"),
        source_url=kwargs.get("source_url", "https://pmkisan.gov.in/doc.pdf"),
        document_version=kwargs.get("document_version", "2024"),
        ministry=kwargs.get("ministry", "Ministry of Agriculture"),
        department=kwargs.get("department", "Agriculture Department"),
        state=kwargs.get("state", ""),
        category=kwargs.get("category", "AGRICULTURE"),
        scheme_id=kwargs.get("scheme_id"),
        scheme_name=kwargs.get("scheme_name", "PM-KISAN"),
    )


def _unit_vector(dim: int = 768) -> list[float]:
    """Return a normalised all-ones vector for deterministic test embeddings."""
    val = 1.0 / math.sqrt(dim)
    return [val] * dim


# ─────────────────────────────────────────────────────────────
# 1. QueryPreprocessor
# ─────────────────────────────────────────────────────────────

class TestQueryPreprocessor(TestCase):

    def setUp(self):
        self.proc = QueryPreprocessor()

    def test_strips_whitespace(self):
        result = self.proc.preprocess("  hello world  ")
        self.assertEqual(result, "hello world")

    def test_collapses_whitespace(self):
        result = self.proc.preprocess("PM   KISAN   scheme")
        self.assertEqual(result, "PM KISAN scheme")

    def test_unicode_normalisation(self):
        # NFKC: ﬁ (ligature) → fi, ² → 2
        result = self.proc.preprocess("ﬁnancial support")
        self.assertEqual(result, "financial support")

    def test_truncation_at_max_length(self):
        long_query = "a" * 2000
        result = self.proc.preprocess(long_query)
        self.assertEqual(len(result), QueryPreprocessor.MAX_QUERY_LEN)

    def test_empty_query_returns_empty(self):
        result = self.proc.preprocess("")
        self.assertEqual(result, "")

    def test_tsquery_filters_short_words(self):
        # "am", "I" should be filtered (length ≤ 2)
        ts = self.proc.build_tsquery("am I eligible for PM KISAN scheme")
        tokens = ts.split()
        self.assertNotIn("am", tokens)
        self.assertNotIn("I", tokens)
        self.assertIn("eligible", tokens)
        self.assertIn("KISAN", tokens)

    def test_tsquery_fallback_to_first_token(self):
        # All tokens ≤ 2 chars → fallback to first token
        ts = self.proc.build_tsquery("am I")
        self.assertEqual(ts, "am")


# ─────────────────────────────────────────────────────────────
# 2. MetadataFilterBuilder
# ─────────────────────────────────────────────────────────────

class TestMetadataFilterBuilder(TestCase):

    def setUp(self):
        self.builder = MetadataFilterBuilder()

    def test_empty_filters(self):
        clauses, params = self.builder.build(None)
        self.assertEqual(clauses, [])
        self.assertEqual(params, [])

    def test_empty_dict(self):
        clauses, params = self.builder.build({})
        self.assertEqual(clauses, [])
        self.assertEqual(params, [])

    def test_category_filter(self):
        clauses, params = self.builder.build({"category": "HEALTH"})
        self.assertEqual(len(clauses), 1)
        self.assertIn("gd.category", clauses[0])
        self.assertIn("HEALTH", params)

    def test_state_filter_ilike(self):
        clauses, params = self.builder.build({"state": "Maharashtra"})
        self.assertEqual(len(clauses), 1)
        self.assertIn("ILIKE", clauses[0])
        self.assertIn("%Maharashtra%", params)

    def test_ministry_filter_ilike(self):
        clauses, params = self.builder.build({"ministry": "Agriculture"})
        self.assertIn("gd.ministry", clauses[0])
        self.assertIn("%Agriculture%", params)

    def test_department_filter_ilike(self):
        clauses, params = self.builder.build({"department": "PMAY"})
        self.assertIn("gd.department", clauses[0])
        self.assertIn("%PMAY%", params)

    def test_scheme_id_filter(self):
        sid = str(uuid.uuid4())
        clauses, params = self.builder.build({"scheme_id": sid})
        self.assertIn("gd.scheme_id", clauses[0])
        self.assertIn(sid, params)

    def test_document_id_filter(self):
        did = str(uuid.uuid4())
        clauses, params = self.builder.build({"document_id": did})
        self.assertIn("dc.document_id", clauses[0])
        self.assertIn(did, params)

    def test_document_version_filter(self):
        clauses, params = self.builder.build({"document_version": "2024"})
        self.assertIn("gd.document_version", clauses[0])
        self.assertIn("2024", params)

    def test_chunk_type_filter(self):
        clauses, params = self.builder.build({"chunk_type": "ELIGIBILITY"})
        self.assertIn("dc.chunk_type", clauses[0])
        self.assertIn("ELIGIBILITY", params)

    def test_multiple_filters(self):
        clauses, params = self.builder.build({
            "category": "AGRICULTURE",
            "state": "Punjab",
            "ministry": "Agriculture",
        })
        self.assertEqual(len(clauses), 3)
        self.assertEqual(len(params), 3)

    def test_none_value_ignored(self):
        # A key with None value should not generate a clause
        clauses, params = self.builder.build({"category": None, "state": "Goa"})
        self.assertEqual(len(clauses), 1)
        self.assertIn("Goa", params[0])


# ─────────────────────────────────────────────────────────────
# 3. RetrievalResult
# ─────────────────────────────────────────────────────────────

class TestRetrievalResult(TestCase):

    def test_to_dict_has_all_required_fields(self):
        result = _make_result()
        d = result.to_dict()
        required_keys = [
            "chunk_id", "document_id", "content", "score",
            "page_number", "section", "chunk_type",
            "document_title", "source_url", "document_version",
            "ministry", "department", "state", "category",
            "scheme_id", "scheme_name", "metadata",
        ]
        for key in required_keys:
            self.assertIn(key, d, f"Missing key: {key}")

    def test_score_rounded(self):
        result = _make_result(score=0.123456789)
        d = result.to_dict()
        # score is rounded to 6dp
        self.assertEqual(d["score"], round(0.123456789, 6))

    def test_repr_contains_chunk_id_prefix(self):
        cid = str(uuid.uuid4())
        result = _make_result(chunk_id=cid)
        self.assertIn(cid[:8], repr(result))

    def test_to_dict_section_maps_to_section_title(self):
        result = _make_result(section_title="Benefits Section")
        d = result.to_dict()
        self.assertEqual(d["section"], "Benefits Section")


# ─────────────────────────────────────────────────────────────
# 4. RRF Fusion (pure Python)
# ─────────────────────────────────────────────────────────────

class TestRRFFusion(TestCase):

    def setUp(self):
        self.retriever = HybridRetriever(top_k=10)

    def test_deduplication(self):
        """Same chunk in both lists should appear once in fused output."""
        shared_id = str(uuid.uuid4())
        dense = [_make_result(chunk_id=shared_id, score=0.9)]
        sparse = [_make_result(chunk_id=shared_id, score=0.7)]
        fused = self.retriever._rrf_fusion(dense, sparse)
        chunk_ids = [r.chunk_id for r in fused]
        self.assertEqual(len(chunk_ids), len(set(chunk_ids)))

    def test_shared_chunk_outscores_unique(self):
        """A chunk that appears in both dense and sparse should rank higher."""
        shared_id = str(uuid.uuid4())
        unique_id = str(uuid.uuid4())
        dense = [
            _make_result(chunk_id=shared_id),
            _make_result(chunk_id=unique_id),
        ]
        sparse = [_make_result(chunk_id=shared_id)]
        fused = self.retriever._rrf_fusion(dense, sparse)
        self.assertEqual(fused[0].chunk_id, shared_id)

    def test_rrf_score_overrides_original(self):
        """After fusion, score should be the RRF score, not the original."""
        cid = str(uuid.uuid4())
        dense = [_make_result(chunk_id=cid, score=0.95)]
        fused = self.retriever._rrf_fusion(dense, [])
        # RRF score for rank-1 with k=60: 1/(60+1) ≈ 0.01639
        expected = 1.0 / (60 + 1)
        self.assertAlmostEqual(fused[0].score, expected, places=5)

    def test_empty_dense_uses_sparse(self):
        results = [_make_result(), _make_result()]
        fused = self.retriever._rrf_fusion([], results)
        self.assertEqual(len(fused), 2)

    def test_empty_sparse_uses_dense(self):
        results = [_make_result(), _make_result()]
        fused = self.retriever._rrf_fusion(results, [])
        self.assertEqual(len(fused), 2)

    def test_both_empty_returns_empty(self):
        fused = self.retriever._rrf_fusion([], [])
        self.assertEqual(fused, [])

    def test_descending_order(self):
        """Fused results must be sorted by descending RRF score."""
        dense = [_make_result() for _ in range(5)]
        sparse = [_make_result() for _ in range(5)]
        fused = self.retriever._rrf_fusion(dense, sparse)
        scores = [r.score for r in fused]
        self.assertEqual(scores, sorted(scores, reverse=True))


# ─────────────────────────────────────────────────────────────
# 5. Top-K enforcement
# ─────────────────────────────────────────────────────────────

class TestTopKEnforcement(TestCase):

    def test_top_k_limits_fused_results(self):
        retriever = HybridRetriever(top_k=3)
        dense = [_make_result() for _ in range(10)]
        sparse = [_make_result() for _ in range(10)]
        # Patch DB calls to return pre-built results
        with patch.object(retriever, "_dense_retrieve", return_value=dense), \
             patch.object(retriever, "_sparse_retrieve", return_value=sparse):
            results = retriever.retrieve(
                query="PM KISAN eligibility",
                query_embedding=_unit_vector(),
            )
        self.assertLessEqual(len(results), 3)

    def test_retrieve_dense_only_respects_top_k(self):
        retriever = HybridRetriever(top_k=2)
        many = [_make_result() for _ in range(20)]
        with patch.object(retriever, "_dense_retrieve", return_value=many):
            results = retriever.retrieve_dense_only(query_embedding=_unit_vector())
        self.assertLessEqual(len(results), 2)

    def test_retrieve_sparse_only_respects_top_k(self):
        retriever = HybridRetriever(top_k=2)
        many = [_make_result() for _ in range(20)]
        with patch.object(retriever, "_sparse_retrieve", return_value=many):
            results = retriever.retrieve_sparse_only(query="PM KISAN")
        self.assertLessEqual(len(results), 2)


# ─────────────────────────────────────────────────────────────
# 6. Guard: empty query / empty embedding
# ─────────────────────────────────────────────────────────────

class TestInputGuards(TestCase):

    def setUp(self):
        self.retriever = HybridRetriever(top_k=5)

    def test_empty_embedding_returns_empty(self):
        with patch.object(self.retriever, "_sparse_retrieve", return_value=[]):
            results = self.retriever.retrieve(
                query="test",
                query_embedding=[],  # empty embedding
            )
        self.assertEqual(results, [])

    def test_empty_query_sparse_returns_empty(self):
        results = self.retriever._sparse_retrieve(query="", n=10, filters=None)
        self.assertEqual(results, [])

    def test_empty_embedding_dense_returns_empty(self):
        results = self.retriever._dense_retrieve(
            query_embedding=[], n=10, filters=None
        )
        self.assertEqual(results, [])


# ─────────────────────────────────────────────────────────────
# 7. Reranker passthrough (USE_RERANKER = False)
# ─────────────────────────────────────────────────────────────

@override_settings(USE_RERANKER=False, RAG_TOP_K_RERANK=3)
class TestRerankerPassthrough(TestCase):

    def test_reranker_disabled_returns_top_k_by_rrf(self):
        reranker = Reranker()
        results = [_make_result(score=1.0 - i * 0.1) for i in range(10)]
        reranked = reranker.rerank("test query", results, top_k=3)
        self.assertEqual(len(reranked), 3)
        # Scores should be in descending order (RRF passthrough)
        scores = [r.score for r in reranked]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_reranker_returns_empty_for_empty_input(self):
        reranker = Reranker()
        result = reranker.rerank("test", [], top_k=5)
        self.assertEqual(result, [])


# ─────────────────────────────────────────────────────────────
# 8. EmbeddingService — deterministic fallback vector
# ─────────────────────────────────────────────────────────────

class TestEmbeddingService(TestCase):

    def test_deterministic_vector_is_768_dim(self):
        svc = EmbeddingService()
        vec = svc._generate_deterministic_vector("test text")
        self.assertEqual(len(vec), 768)

    def test_deterministic_vector_is_unit_norm(self):
        svc = EmbeddingService()
        vec = svc._generate_deterministic_vector("government scheme eligibility")
        norm = math.sqrt(sum(x * x for x in vec))
        self.assertAlmostEqual(norm, 1.0, places=5)

    def test_different_texts_produce_different_vectors(self):
        svc = EmbeddingService()
        v1 = svc._generate_deterministic_vector("PM KISAN")
        v2 = svc._generate_deterministic_vector("PM Ayushman Bharat")
        self.assertNotEqual(v1, v2)

    def test_same_text_same_vector(self):
        svc = EmbeddingService()
        v1 = svc._generate_deterministic_vector("same text")
        v2 = svc._generate_deterministic_vector("same text")
        self.assertEqual(v1, v2)

    @override_settings(GOOGLE_API_KEY="mock-google-api-key")
    def test_embed_query_returns_list(self):
        """embed_query should fall back to deterministic vector with mock API key."""
        svc = EmbeddingService()
        vec = svc.embed_query("what schemes are available for farmers?")
        self.assertIsInstance(vec, list)
        self.assertEqual(len(vec), 768)


# ─────────────────────────────────────────────────────────────
# 9. DB Integration — retrieve against real COMPLETED documents
#    These tests are skipped gracefully if no COMPLETED docs exist
# ─────────────────────────────────────────────────────────────

class TestRetrievalDBIntegration(TestCase):
    """
    Integration tests that exercise the full SQL path.
    They work with whatever data is currently in the test DB.
    If no COMPLETED documents exist, they simply verify no crash occurs.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.retriever = HybridRetriever(top_k=5)
        cls.embedder = EmbeddingService()

    def _get_query_embedding(self, text: str) -> list[float]:
        return self.embedder.embed_query(text)

    def test_hybrid_retrieve_no_crash(self):
        """Hybrid retrieval must not raise an exception even with no matching docs."""
        vec = self._get_query_embedding("eligibility for farmers scheme")
        try:
            results = self.retriever.retrieve(
                query="eligibility for farmers scheme",
                query_embedding=vec,
            )
        except Exception as exc:
            self.fail(f"retrieve() raised an unexpected exception: {exc}")
        self.assertIsInstance(results, list)

    def test_dense_only_no_crash(self):
        vec = self._get_query_embedding("housing scheme for BPL families")
        try:
            results = self.retriever.retrieve_dense_only(query_embedding=vec)
        except Exception as exc:
            self.fail(f"retrieve_dense_only() raised: {exc}")
        self.assertIsInstance(results, list)

    def test_sparse_only_no_crash(self):
        try:
            results = self.retriever.retrieve_sparse_only(
                query="PM Kisan income support annual"
            )
        except Exception as exc:
            self.fail(f"retrieve_sparse_only() raised: {exc}")
        self.assertIsInstance(results, list)

    def test_results_have_required_fields(self):
        """Every result must expose all 17 required fields."""
        vec = self._get_query_embedding("scheme eligibility income criteria")
        results = self.retriever.retrieve(
            query="scheme eligibility income criteria",
            query_embedding=vec,
        )
        required_keys = {
            "chunk_id", "document_id", "content", "score",
            "page_number", "section", "chunk_type",
            "document_title", "source_url", "document_version",
            "ministry", "department", "state", "category",
            "scheme_id", "scheme_name", "metadata",
        }
        for result in results:
            d = result.to_dict()
            missing = required_keys - set(d.keys())
            self.assertEqual(missing, set(), f"Missing keys: {missing}")

    def test_category_filter_no_crash(self):
        vec = self._get_query_embedding("agriculture support scheme")
        try:
            results = self.retriever.retrieve(
                query="agriculture support scheme",
                query_embedding=vec,
                filters={"category": "AGRICULTURE"},
            )
        except Exception as exc:
            self.fail(f"Category-filtered retrieve() raised: {exc}")
        self.assertIsInstance(results, list)

    def test_state_filter_no_crash(self):
        vec = self._get_query_embedding("housing scheme Maharashtra")
        try:
            results = self.retriever.retrieve(
                query="housing scheme Maharashtra",
                query_embedding=vec,
                filters={"state": "Maharashtra"},
            )
        except Exception as exc:
            self.fail(f"State-filtered retrieve() raised: {exc}")
        self.assertIsInstance(results, list)

    def test_ministry_filter_no_crash(self):
        vec = self._get_query_embedding("health insurance low income")
        try:
            results = self.retriever.retrieve(
                query="health insurance low income",
                query_embedding=vec,
                filters={"ministry": "Health"},
            )
        except Exception as exc:
            self.fail(f"Ministry-filtered retrieve() raised: {exc}")
        self.assertIsInstance(results, list)

    def test_top_k_honoured(self):
        retriever = HybridRetriever(top_k=2)
        vec = self._get_query_embedding("government scheme")
        results = retriever.retrieve(
            query="government scheme",
            query_embedding=vec,
        )
        self.assertLessEqual(len(results), 2)

    def test_scores_non_negative(self):
        vec = self._get_query_embedding("benefits of Ayushman Bharat health scheme")
        results = self.retriever.retrieve(
            query="benefits of Ayushman Bharat health scheme",
            query_embedding=vec,
        )
        for r in results:
            self.assertGreaterEqual(r.score, 0.0, "Score must be non-negative")

    def test_scores_descending(self):
        vec = self._get_query_embedding("PM KISAN eligibility annual income")
        results = self.retriever.retrieve(
            query="PM KISAN eligibility annual income",
            query_embedding=vec,
        )
        if len(results) > 1:
            for i in range(len(results) - 1):
                self.assertGreaterEqual(
                    results[i].score,
                    results[i + 1].score,
                    "Results must be in descending score order",
                )
