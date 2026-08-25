"""
rag/citation_builder.py

Builds grounded context and citation objects from RetrievalResult objects.

The builder is intentionally defensive because chunk metadata may arrive as:
    - dict
    - JSON string
    - None
    - unexpected primitive value

All citation data is therefore normalized before accessing metadata.
"""

import json
import logging
import re
from typing import Any, Iterable, Optional

logger = logging.getLogger(__name__)


class CitationBuilder:
    """
    Builds citation data and grounded context for the RAG pipeline.
    """

    # ============================================================
    # METADATA NORMALIZATION
    # ============================================================

    @staticmethod
    def _normalize_metadata(metadata: Any) -> dict:
        """
        Convert metadata into a safe dictionary.

        Supported:
            dict
            JSON string containing an object
            None
            unexpected values

        Unexpected values are converted into an empty dictionary
        rather than crashing the RAG pipeline.
        """

        if metadata is None:
            return {}

        if isinstance(metadata, dict):
            return metadata

        if isinstance(metadata, str):

            value = metadata.strip()

            if not value:
                return {}

            try:
                parsed = json.loads(value)

                if isinstance(parsed, dict):
                    return parsed

            except (json.JSONDecodeError, TypeError, ValueError):
                pass

            # Metadata is a plain string rather than JSON.
            # Keep it available for debugging without treating it
            # like a dictionary.
            return {
                "raw_metadata": value,
            }

        # Handle Django JSONField-like mapping objects.
        try:
            if hasattr(metadata, "items"):
                return dict(metadata)
        except Exception:
            pass

        return {}

    # ============================================================
    # SAFE VALUE HELPERS
    # ============================================================

    @staticmethod
    def _safe_value(
        result: Any,
        attribute: str,
        metadata: dict,
        metadata_key: Optional[str] = None,
        default: str = "",
    ) -> str:
        """
        Get a value from RetrievalResult first, then metadata.
        """

        value = getattr(result, attribute, None)

        if value not in (None, ""):
            return str(value)

        key = metadata_key or attribute

        meta_value = metadata.get(key, default)

        if meta_value in (None, ""):
            return default

        return str(meta_value)

    @staticmethod
    def _safe_int(
        result: Any,
        attribute: str,
        metadata: dict,
        metadata_key: Optional[str] = None,
    ) -> Optional[int]:
        """
        Safely extract integer metadata such as page number.
        """

        value = getattr(result, attribute, None)

        if value in (None, ""):
            key = metadata_key or attribute
            value = metadata.get(key)

        if value in (None, ""):
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    # ============================================================
    # BUILD CONTEXT BLOCK
    # ============================================================

    def build_context_block(
        self,
        results: Iterable[Any],
    ) -> str:
        """
        Convert retrieved results into grounded LLM context.

        Each result contains provenance information so that the
        generator can answer using official source material.
        """

        results = list(results or [])

        if not results:
            return ""

        blocks = []

        for index, result in enumerate(results, start=1):

            metadata = self._normalize_metadata(
                getattr(result, "metadata", None)
            )

            content = getattr(
                result,
                "content",
                "",
            ) or ""

            content = str(content).strip()

            if not content:
                continue

            scheme_name = self._safe_value(
                result,
                "scheme_name",
                metadata,
                "scheme_name",
            )

            document_title = self._safe_value(
                result,
                "document_title",
                metadata,
                "document_title",
            )

            ministry = self._safe_value(
                result,
                "ministry",
                metadata,
                "ministry",
            )

            department = self._safe_value(
                result,
                "department",
                metadata,
                "department",
            )

            page_number = self._safe_int(
                result,
                "page_number",
                metadata,
                "page_number",
            )

            section_title = self._safe_value(
                result,
                "section_title",
                metadata,
                "section",
            )

            source_url = self._safe_value(
                result,
                "source_url",
                metadata,
                "source_url",
            )

            document_version = self._safe_value(
                result,
                "document_version",
                metadata,
                "document_version",
            )

            chunk_type = self._safe_value(
                result,
                "chunk_type",
                metadata,
                "chunk_type",
                "TEXT",
            )

            header_lines = [
                f"[SOURCE {index}]",
            ]

            if scheme_name:
                header_lines.append(
                    f"Scheme: {scheme_name}"
                )

            if document_title:
                header_lines.append(
                    f"Document: {document_title}"
                )

            if ministry:
                header_lines.append(
                    f"Ministry: {ministry}"
                )

            if department:
                header_lines.append(
                    f"Department: {department}"
                )

            if page_number is not None:
                header_lines.append(
                    f"Page: {page_number}"
                )

            if section_title:
                header_lines.append(
                    f"Section: {section_title}"
                )

            if chunk_type:
                header_lines.append(
                    f"Chunk Type: {chunk_type}"
                )

            if document_version:
                header_lines.append(
                    f"Document Version: {document_version}"
                )

            if source_url:
                header_lines.append(
                    f"Source URL: {source_url}"
                )

            block = (
                "\n".join(header_lines)
                + "\n\n"
                + content
            )

            blocks.append(block)

        return "\n\n---\n\n".join(blocks)

    # ============================================================
    # BUILD CITATIONS
    # ============================================================

    def build_citations(
        self,
        results: Iterable[Any],
    ) -> list[dict]:
        """
        Build frontend-friendly citation objects.

        IMPORTANT:
        Metadata is normalized before .get() is used.
        This fixes the previous:

            AttributeError:
            'str' object has no attribute 'get'
        """

        results = list(results or [])

        citations = []

        for index, result in enumerate(results, start=1):

            try:

                metadata = self._normalize_metadata(
                    getattr(result, "metadata", None)
                )

                # ------------------------------------------------
                # Basic provenance
                # ------------------------------------------------

                chunk_id = self._safe_value(
                    result,
                    "chunk_id",
                    metadata,
                    "chunk_id",
                )

                document_id = self._safe_value(
                    result,
                    "document_id",
                    metadata,
                    "document_id",
                )

                scheme_id = self._safe_value(
                    result,
                    "scheme_id",
                    metadata,
                    "scheme_id",
                )

                scheme_name = self._safe_value(
                    result,
                    "scheme_name",
                    metadata,
                    "scheme_name",
                )

                document_title = self._safe_value(
                    result,
                    "document_title",
                    metadata,
                    "document_title",
                )

                source_url = self._safe_value(
                    result,
                    "source_url",
                    metadata,
                    "source_url",
                )

                document_version = self._safe_value(
                    result,
                    "document_version",
                    metadata,
                    "document_version",
                )

                ministry = self._safe_value(
                    result,
                    "ministry",
                    metadata,
                    "ministry",
                )

                department = self._safe_value(
                    result,
                    "department",
                    metadata,
                    "department",
                )

                state = self._safe_value(
                    result,
                    "state",
                    metadata,
                    "state",
                )

                category = self._safe_value(
                    result,
                    "category",
                    metadata,
                    "category",
                )

                section_title = self._safe_value(
                    result,
                    "section_title",
                    metadata,
                    "section",
                )

                chunk_type = self._safe_value(
                    result,
                    "chunk_type",
                    metadata,
                    "chunk_type",
                    "TEXT",
                )

                page_number = self._safe_int(
                    result,
                    "page_number",
                    metadata,
                    "page_number",
                )

                score = getattr(
                    result,
                    "score",
                    0.0,
                )

                try:
                    score = float(score or 0.0)
                except (TypeError, ValueError):
                    score = 0.0

                content = getattr(
                    result,
                    "content",
                    "",
                ) or ""

                # ------------------------------------------------
                # Citation title
                # ------------------------------------------------

                title = (
                    scheme_name
                    or document_title
                    or "Government Scheme Document"
                )

                # ------------------------------------------------
                # Citation object
                # ------------------------------------------------

                citation = {
                    "id": index,

                    "citation_id": index,

                    "chunk_id": chunk_id,

                    "document_id": document_id,

                    "scheme_id": scheme_id,

                    "scheme_name": scheme_name,

                    "title": title,

                    "document_title": document_title,

                    "page": page_number,

                    "page_number": page_number,

                    "section": section_title,

                    "section_title": section_title,

                    "chunk_type": chunk_type,

                    "ministry": ministry,

                    "department": department,

                    "state": state,

                    "category": category,

                    "source_url": source_url,

                    "url": source_url,

                    "document_version": document_version,

                    "version": document_version,

                    "score": round(score, 6),

                    "content": content,

                    "snippet": self._make_snippet(
                        content
                    ),

                    "metadata": metadata,
                }

                citations.append(citation)

            except Exception as exc:

                # One malformed citation must never break
                # the complete RAG answer.

                logger.exception(
                    "Failed to build citation for result %s: %s",
                    index,
                    exc,
                )

                continue

        return citations

    # ============================================================
    # SNIPPET
    # ============================================================

    @staticmethod
    def _make_snippet(
        content: str,
        max_length: int = 300,
    ) -> str:
        """
        Create a short citation preview for the frontend.
        """

        if not content:
            return ""

        text = re.sub(
            r"\s+",
            " ",
            str(content),
        ).strip()

        if len(text) <= max_length:
            return text

        return (
            text[: max_length - 3].rstrip()
            + "..."
        )

    # ============================================================
    # ANNOTATE RESPONSE
    # ============================================================

    def annotate_response(
        self,
        answer: str,
        citations: list[dict],
    ) -> str:
        """
        Add citation markers to the response when the LLM already
        references sources.

        The method deliberately avoids inventing citations.
        """

        if not answer:
            return answer

        if not citations:
            return answer

        text = str(answer)

        # If the generator already added citation markers,
        # don't duplicate them.
        existing_markers = re.findall(
            r"\[\d+\]",
            text,
        )

        if existing_markers:
            return text

        # Do not force artificial citation markers into every
        # sentence. The frontend already receives structured
        # citations separately.
        return text

    # ============================================================
    # UTILITY
    # ============================================================

    def get_primary_citation(
        self,
        citations: list[dict],
    ) -> Optional[dict]:
        """
        Return the highest-ranked citation.
        """

        if not citations:
            return None

        return citations[0]

    def deduplicate_citations(
        self,
        citations: list[dict],
    ) -> list[dict]:
        """
        Remove duplicate document/page citations.
        """

        unique = []
        seen = set()

        for citation in citations:

            key = (
                citation.get("document_id", ""),
                citation.get("page_number"),
                citation.get("section_title", ""),
            )

            if key in seen:
                continue

            seen.add(key)
            unique.append(citation)

        return unique