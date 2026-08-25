"""
rag/retriever.py

Local-safe RAG retrieval layer.

Current local database:
    document_chunks has NO embedding column.

Therefore normal retrieval uses:
    Query preprocessing
        ↓
    Scheme detection
        ↓
    PostgreSQL Full-Text Search
        ↓
    Scheme-aware filtering
        ↓
    Top-K RetrievalResult

Dense pgvector methods are retained only for future compatibility.
"""

import logging
import re
import unicodedata
from typing import Optional

from django.conf import settings
from django.db import connection


logger = logging.getLogger(__name__)


# ============================================================
# RetrievalResult
# ============================================================

class RetrievalResult:
    """
    Single retrieved document chunk with provenance metadata.
    """

    __slots__ = (
        "chunk_id",
        "document_id",
        "content",
        "score",
        "metadata",
        "page_number",
        "section_title",
        "chunk_type",
        "document_title",
        "source_url",
        "document_version",
        "ministry",
        "department",
        "state",
        "category",
        "scheme_id",
        "scheme_name",
    )

    def __init__(
        self,
        *,
        chunk_id: str,
        document_id: str,
        content: str,
        score: float,
        metadata: dict,
        page_number: Optional[int] = None,
        section_title: str = "",
        chunk_type: str = "TEXT",
        document_title: str = "",
        source_url: str = "",
        document_version: str = "",
        ministry: str = "",
        department: str = "",
        state: str = "",
        category: str = "",
        scheme_id: Optional[str] = None,
        scheme_name: str = "",
    ):
        self.chunk_id = chunk_id
        self.document_id = document_id
        self.content = content
        self.score = score
        self.metadata = metadata
        self.page_number = page_number
        self.section_title = section_title
        self.chunk_type = chunk_type
        self.document_title = document_title
        self.source_url = source_url
        self.document_version = document_version
        self.ministry = ministry
        self.department = department
        self.state = state
        self.category = category
        self.scheme_id = scheme_id
        self.scheme_name = scheme_name

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "content": self.content,
            "score": round(float(self.score), 6),
            "page_number": self.page_number,
            "section": self.section_title,
            "chunk_type": self.chunk_type,
            "document_title": self.document_title,
            "source_url": self.source_url,
            "document_version": self.document_version,
            "ministry": self.ministry,
            "department": self.department,
            "state": self.state,
            "category": self.category,
            "scheme_id": self.scheme_id,
            "scheme_name": self.scheme_name,
            "metadata": self.metadata,
        }

    def __repr__(self) -> str:
        return (
            f"<RetrievalResult "
            f"chunk={self.chunk_id[:8]} "
            f"score={self.score:.4f} "
            f"type={self.chunk_type}>"
        )


# ============================================================
# Query Preprocessor
# ============================================================

class QueryPreprocessor:
    """
    Cleans and normalises user queries.
    """

    MAX_QUERY_LEN = 1024

    ACRONYM_TERMS = {
        "bscc": "Bihar Student Credit Card",
        "ssy": "Sukanya Samriddhi",
        "pmkisan": "PM Kisan Samman Nidhi",
        "pmuy": "Ujjwala LPG",
        "pmjay": "Ayushman Bharat Jan Arogya",
        "pmfby": "Fasal Bima",
        "pmay": "Awas Yojana",
        "apy": "Atal Pension",
        "svanidhi": "SVANidhi Street Vendor",
        "mjpjay": "Jyotirao Phule Jan Arogya",
        "mkuy": "Kanya Utthan",
        "nsap": "Social Assistance IGNOAPS",
    }

    def preprocess(self, query: str) -> str:

        if not query:
            return ""

        query = unicodedata.normalize(
            "NFKC",
            str(query),
        )

        query = query.strip()

        query = re.sub(
            r"\s+",
            " ",
            query,
        )

        query = re.sub(
            r"[^\x20-\x7E\u00A0-\uFFFF]",
            "",
            query,
        )

        return query[: self.MAX_QUERY_LEN]

    def build_tsquery(self, query: str) -> str:

        if not query:
            return ""

        raw_tokens = [
            word
            for word in re.findall(
                r"[a-zA-Z0-9\-]+",
                query,
            )
            if len(word) > 2
        ]

        expanded_tokens = list(raw_tokens)

        for token in raw_tokens:

            clean_token = token.lower().replace(
                "-",
                "",
            )

            if clean_token in self.ACRONYM_TERMS:

                expanded_tokens.extend(
                    self.ACRONYM_TERMS[
                        clean_token
                    ].split()
                )

        tokens = [
            word
            for word in expanded_tokens
            if len(word) > 2
        ]

        if tokens:
            return " ".join(tokens)

        return query


# ============================================================
# MetadataFilterBuilder
# ============================================================

class MetadataFilterBuilder:

    def build(
        self,
        filters: Optional[dict],
    ) -> tuple[list[str], list]:

        clauses = []
        params = []

        if not filters:
            return clauses, params

        mapping = {
            "category": (
                "gd.category",
                "=",
            ),
            "document_version": (
                "gd.document_version",
                "=",
            ),
            "document_id": (
                "dc.document_id",
                "=",
            ),
            "chunk_type": (
                "dc.chunk_type",
                "=",
            ),
        }

        ilike_mapping = {
            "state": "gd.state",
            "ministry": "gd.ministry",
            "department": "gd.department",
        }

        for key, (
            column,
            operator,
        ) in mapping.items():

            value = filters.get(key)

            if value:

                clauses.append(
                    f"{column} {operator} %s"
                )

                params.append(
                    str(value)
                )

        for key, column in ilike_mapping.items():

            value = filters.get(key)

            if value:

                clauses.append(
                    f"{column} ILIKE %s"
                )

                params.append(
                    f"%{value}%"
                )

        scheme_id = filters.get(
            "scheme_id"
        )

        if scheme_id:

            clauses.append(
                "gd.scheme_id = %s"
            )

            params.append(
                str(scheme_id)
            )

        return clauses, params


# ============================================================
# HybridRetriever
# ============================================================

class HybridRetriever:

    _BASE_SELECT = """
        SELECT
            dc.id                   AS chunk_id,
            dc.document_id          AS document_id,
            dc.content              AS content,
            dc.page_number         AS page_number,
            dc.section_title       AS section_title,
            dc.chunk_type           AS chunk_type,
            dc.metadata             AS metadata,

            gd.title                AS document_title,
            gd.source_url           AS source_url,
            gd.document_version     AS document_version,
            gd.ministry             AS ministry,
            gd.department           AS department,
            gd.state                AS state,
            gd.category             AS category,
            gd.scheme_id            AS scheme_id,

            COALESCE(
                gs.name,
                ''
            )                       AS scheme_name
    """

    _BASE_FROM = """
        FROM document_chunks dc

        INNER JOIN gov_documents gd
            ON dc.document_id = gd.id

        LEFT JOIN government_schemes gs
            ON gd.scheme_id = gs.id
    """

    _BASE_WHERE = """
        WHERE gd.status = 'COMPLETED'
    """

    # ========================================================
    # Scheme patterns
    # ========================================================

    SCHEME_PATTERNS = {

        "pm-kisan": [
            "pm-kisan",
            "pm kisan",
            "pmkisan",
            "pradhan mantri kisan samman nidhi",
        ],

        "pmay": [
            "pmay",
            "pmay-u",
            "pmayu",
            "pmay-g",
            "pmayg",
            "pradhan mantri awas yojana",
        ],

        "pmuy": [
            "pmuy",
            "ujjwala yojana",
            "pradhan mantri ujjwala",
        ],

        "apy": [
            "atal pension yojana",
            "atal pension",
        ],

        "pmjay": [
            "pm-jay",
            "pmjay",
            "ayushman bharat",
            "jan arogya yojana",
        ],

        "pmfby": [
            "pmfby",
            "pradhan mantri fasal bima",
            "fasal bima yojana",
        ],

        "bscc": [
            "bihar student credit card",
            "bscc",
        ],

        "ssy": [
            "sukanya samriddhi",
            "sukanya samriddhi yojana",
            "ssy",
        ],

        "nsap": [
            "national social assistance programme",
            "national social assistance program",
            "nsap",
        ],

        "svanidhi": [
            "pm svanidhi",
            "pm-svanidhi",
            "svanidhi",
        ],

        "mjpjay": [
            "mahatma jyotirao phule",
            "mjpjay",
            "jyotirao phule jan arogya",
        ],

        "mkuy": [
            "mukhyamantri kanya utthan",
            "mkuy",
            "kanya utthan",
        ],
    }

    # ========================================================
    # Scheme SQL keywords
    # ========================================================

    SCHEME_SEARCH_KEYWORDS = {

        "pm-kisan": [
            "pm-kisan",
            "pm kisan",
            "pmkisan",
            "pradhan mantri kisan samman nidhi",
        ],

        "pmay": [
            "pmay",
            "pradhan mantri awas yojana",
        ],

        "pmuy": [
            "pmuy",
            "ujjwala",
            "pradhan mantri ujjwala",
        ],

        "apy": [
            "atal pension",
            "atal pension yojana",
        ],

        "pmjay": [
            "pm-jay",
            "pmjay",
            "ayushman bharat",
            "jan arogya",
        ],

        "pmfby": [
            "pmfby",
            "fasal bima",
        ],

        "bscc": [
            "bihar student credit card",
            "bscc",
        ],

        "ssy": [
            "sukanya samriddhi",
            "sukanya samriddhi yojana",
        ],

        "nsap": [
            "national social assistance",
            "nsap",
        ],

        "svanidhi": [
            "pm svanidhi",
            "pm-svanidhi",
            "svanidhi",
        ],

        "mjpjay": [
            "mahatma jyotirao phule",
            "mjpjay",
            "jan arogya",
        ],

        "mkuy": [
            "mukhyamantri kanya utthan",
            "mkuy",
            "kanya utthan",
        ],
    }

    # ========================================================
    # Init
    # ========================================================

    def __init__(
        self,
        top_k: int = None,
        rrf_k: int = 60,
    ):

        self.top_k = (
            top_k
            or getattr(
                settings,
                "RAG_TOP_K_RETRIEVE",
                20,
            )
        )

        self.rrf_k = rrf_k

        self._filter_builder = (
            MetadataFilterBuilder()
        )

        self._preprocessor = (
            QueryPreprocessor()
        )

    # ========================================================
    # Scheme detection
    # ========================================================

    def _detect_scheme_filter(
        self,
        query: str,
    ) -> Optional[str]:

        if not query:
            return None

        q = query.lower().strip()

        candidates = []

        for scheme_key, patterns in (
            self.SCHEME_PATTERNS.items()
        ):

            for pattern in patterns:

                candidates.append(
                    (
                        len(pattern),
                        scheme_key,
                        pattern,
                    )
                )

        candidates.sort(
            reverse=True
        )

        for _, scheme_key, pattern in candidates:

            if pattern in q:
                return scheme_key

        return None

    # ========================================================
    # Main retrieval
    # ========================================================

    def retrieve(
        self,
        query: str,
        query_embedding: list[float] | None = None,
        filters: Optional[dict] = None,
    ) -> list[RetrievalResult]:

        query = self._preprocessor.preprocess(
            query
        )

        if not query:
            return []

        pool_size = max(
            self.top_k * 3,
            30,
        )

        effective_filters = dict(
            filters or {}
        )

        scheme_filter = (
            self._detect_scheme_filter(
                query
            )
        )

        if scheme_filter:

            effective_filters[
                "_scheme_keyword"
            ] = scheme_filter

            logger.info(
                "Scheme detected for retrieval: %s",
                scheme_filter,
            )

        sparse_results = (
            self._sparse_retrieve(
                query,
                pool_size,
                effective_filters,
            )
        )

        results = sparse_results[
            : self.top_k
        ]

        logger.info(
            "Local retrieval complete: "
            "scheme=%s sparse=%d returned=%d",
            scheme_filter,
            len(sparse_results),
            len(results),
        )

        return results

    # ========================================================
    # Sparse only
    # ========================================================

    def retrieve_sparse_only(
        self,
        query: str,
        filters: Optional[dict] = None,
        top_k: Optional[int] = None,
    ) -> list[RetrievalResult]:

        query = self._preprocessor.preprocess(
            query
        )

        n = (
            top_k
            or self.top_k
        )

        scheme_filter = (
            self._detect_scheme_filter(
                query
            )
        )

        effective_filters = dict(
            filters or {}
        )

        if scheme_filter:

            effective_filters[
                "_scheme_keyword"
            ] = scheme_filter

        results = (
            self._sparse_retrieve(
                query,
                n,
                effective_filters,
            )
        )

        return results[:n]

    # ========================================================
    # Dense compatibility method
    # ========================================================

    def retrieve_dense_only(
        self,
        query_embedding: list[float],
        filters: Optional[dict] = None,
        top_k: Optional[int] = None,
    ) -> list[RetrievalResult]:

        logger.warning(
            "Dense retrieval is disabled because "
            "document_chunks.embedding does not exist "
            "in the current local database."
        )

        return []

    # ========================================================
    # Sparse retrieval
    # ========================================================

    def _sparse_retrieve(
        self,
        query: str,
        n: int,
        filters: Optional[dict],
    ) -> list[RetrievalResult]:

        if not query:
            return []

        where_clauses, params = (
            self._filter_builder.build(
                filters
            )
        )

        # ----------------------------------------------------
        # Scheme filter
        # ----------------------------------------------------

        scheme_keyword = None

        if filters:

            scheme_keyword = filters.get(
                "_scheme_keyword"
            )

        if scheme_keyword:

            keywords = (
                self.SCHEME_SEARCH_KEYWORDS.get(
                    scheme_keyword,
                    [],
                )
            )

            if keywords:

                scheme_conditions = []

                for keyword in keywords:

                    like_value = (
                        f"%{keyword.lower()}%"
                    )

                    scheme_conditions.append(
                        """
                        (
                            LOWER(
                                COALESCE(
                                    gs.name,
                                    ''
                                )
                            ) LIKE %s

                            OR

                            LOWER(
                                COALESCE(
                                    gd.title,
                                    ''
                                )
                            ) LIKE %s

                            OR

                            LOWER(
                                COALESCE(
                                    dc.metadata::text,
                                    ''
                                )
                            ) LIKE %s
                        )
                        """
                    )

                    params.extend(
                        [
                            like_value,
                            like_value,
                            like_value,
                        ]
                    )

                where_clauses.append(
                    "("
                    + " OR ".join(
                        scheme_conditions
                    )
                    + ")"
                )

        # ----------------------------------------------------
        # WHERE
        # ----------------------------------------------------

        extra_where = ""

        if where_clauses:

            extra_where = (
                " AND "
                + " AND ".join(
                    where_clauses
                )
            )

        # ----------------------------------------------------
        # FTS
        # ----------------------------------------------------

        clean_query = (
            self._preprocessor.build_tsquery(
                query
            )
        )

        sql = f"""
            {self._BASE_SELECT},

            ts_rank(
                to_tsvector(
                    'english',
                    COALESCE(
                        dc.content,
                        ''
                    )
                ),
                plainto_tsquery(
                    'english',
                    %s
                )
            ) AS score

            {self._BASE_FROM}

            {self._BASE_WHERE}

            AND (
                to_tsvector(
                    'english',
                    COALESCE(
                        dc.content,
                        ''
                    )
                )
                @@ websearch_to_tsquery(
                    'english',
                    %s
                )

                OR

                to_tsvector(
                    'english',
                    COALESCE(
                        dc.content,
                        ''
                    )
                )
                @@ plainto_tsquery(
                    'english',
                    %s
                )
            )

            {extra_where}

            ORDER BY
                score DESC,
                dc.page_number ASC,
                dc.chunk_index ASC

            LIMIT %s
        """

        all_params = (
            [clean_query]
            + [query]
            + [clean_query]
            + params
            + [n]
        )

        try:

            with connection.cursor() as cursor:

                cursor.execute(
                    sql,
                    all_params,
                )

                rows = cursor.fetchall()

        except Exception as exc:

            logger.warning(
                "Sparse retrieval SQL error: %s",
                exc,
            )

            return []

        results = (
            self._rows_to_results(
                rows
            )
        )

        # ----------------------------------------------------
        # Final safety filter
        # ----------------------------------------------------

        if scheme_keyword:

            results = (
                self._final_scheme_filter(
                    results,
                    scheme_keyword,
                )
            )

        logger.debug(
            "Sparse retrieval: "
            "scheme=%s returned=%d",
            scheme_keyword,
            len(results),
        )

        return results

    # ========================================================
    # Final scheme safety filter
    # ========================================================

    def _final_scheme_filter(
        self,
        results: list[RetrievalResult],
        scheme_keyword: str,
    ) -> list[RetrievalResult]:

        keywords = (
            self.SCHEME_SEARCH_KEYWORDS.get(
                scheme_keyword,
                [],
            )
        )

        if not keywords:
            return results

        filtered = []

        for result in results:

            searchable_text = " ".join(
                [
                    result.scheme_name or "",
                    result.document_title or "",
                    result.content or "",
                    str(
                        result.metadata or {}
                    ),
                ]
            ).lower()

            if any(
                keyword.lower()
                in searchable_text
                for keyword in keywords
            ):

                filtered.append(
                    result
                )

        return filtered

    # ========================================================
    # SQL rows → RetrievalResult
    # ========================================================

    def _rows_to_results(
        self,
        rows,
    ) -> list[RetrievalResult]:

        results = []

        for row in rows:

            if len(row) != 17:

                logger.warning(
                    "Unexpected retrieval row length: %d",
                    len(row),
                )

                continue

            (
                chunk_id,
                document_id,
                content,
                page_number,
                section_title,
                chunk_type,
                metadata,
                document_title,
                source_url,
                document_version,
                ministry,
                department,
                state,
                category,
                scheme_id,
                scheme_name,
                score,
            ) = row

            results.append(
                RetrievalResult(
                    chunk_id=str(
                        chunk_id
                    ),

                    document_id=str(
                        document_id
                    ),

                    content=(
                        content or ""
                    ),

                    score=float(
                        score or 0.0
                    ),

                    metadata=(
                        metadata or {}
                    ),

                    page_number=page_number,

                    section_title=(
                        section_title or ""
                    ),

                    chunk_type=(
                        chunk_type or "TEXT"
                    ),

                    document_title=(
                        document_title or ""
                    ),

                    source_url=(
                        source_url or ""
                    ),

                    document_version=(
                        document_version or ""
                    ),

                    ministry=(
                        ministry or ""
                    ),

                    department=(
                        department or ""
                    ),

                    state=(
                        state or ""
                    ),

                    category=(
                        category or ""
                    ),

                    scheme_id=(
                        str(scheme_id)
                        if scheme_id
                        else None
                    ),

                    scheme_name=(
                        scheme_name or ""
                    ),
                )
            )

        return results

    # ========================================================
    # RRF compatibility
    # ========================================================

    def _rrf_fusion(
        self,
        dense_results: list[RetrievalResult],
        sparse_results: list[RetrievalResult],
    ) -> list[RetrievalResult]:

        rrf_scores = {}
        chunk_map = {}

        for rank, result in enumerate(
            dense_results,
            start=1,
        ):

            chunk_id = result.chunk_id

            rrf_scores[chunk_id] = (
                rrf_scores.get(
                    chunk_id,
                    0.0,
                )
                + 1.0
                / (
                    self.rrf_k
                    + rank
                )
            )

            chunk_map[
                chunk_id
            ] = result

        for rank, result in enumerate(
            sparse_results,
            start=1,
        ):

            chunk_id = result.chunk_id

            rrf_scores[chunk_id] = (
                rrf_scores.get(
                    chunk_id,
                    0.0,
                )
                + 1.0
                / (
                    self.rrf_k
                    + rank
                )
            )

            if chunk_id not in chunk_map:

                chunk_map[
                    chunk_id
                ] = result

        fused = []

        for chunk_id in sorted(
            rrf_scores,
            key=rrf_scores.get,
            reverse=True,
        ):

            result = (
                chunk_map[
                    chunk_id
                ]
            )

            result.score = (
                rrf_scores[
                    chunk_id
                ]
            )

            fused.append(
                result
            )

        return fused