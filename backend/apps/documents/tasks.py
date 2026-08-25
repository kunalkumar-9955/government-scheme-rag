"""
apps/documents/tasks.py — Async document processing Celery tasks
Implements the full ingestion pipeline:
Upload → File Validation → Text Extraction → Cleaning → Section Detection → Metadata Extraction → Chunking → Embedding Generation → Vector Storage
"""
import logging
from datetime import datetime
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    queue="documents",
    name="apps.documents.tasks.process_document",
)
def process_document(self, document_id: str):
    """
    Full document ingestion pipeline:
      1. Parse PDF / DOCX / HTML → raw text + page numbers + structure
      2. Clean extracted text
      3. Detect sections and headings
      4. Chunk document preserving page numbers and all 11 metadata fields
      5. Generate embeddings in batches
      6. Store chunks and vector embeddings
    """
    from apps.documents.models import GovDocument, DocumentStatus

    try:
        doc = GovDocument.objects.select_related("scheme").get(id=document_id)
    except GovDocument.DoesNotExist:
        logger.error("Document %s not found for processing", document_id)
        return

    logger.info("Starting ingestion pipeline for document: %s (id=%s)", doc.title, doc.id)

    try:
        # ── Step 1: Text Extraction & Structure Parsing ──
        _update_status(doc, DocumentStatus.PROCESSING)
        parsed_content = _parse_document(doc)
        doc.page_count = parsed_content.get("metadata", {}).get("page_count", 1)
        doc.save(update_fields=["page_count"])

        # ── Step 2: Chunk Document with Section Detection & Metadata ──
        _update_status(doc, DocumentStatus.CHUNKING)
        chunks = _chunk_document(doc, parsed_content)
        logger.info("Document %s produced %d chunks", doc.title, len(chunks))

        # ── Step 3: Generate Embeddings + Vector Storage ──
        _update_status(doc, DocumentStatus.EMBEDDING)
        _embed_and_store_chunks(doc, chunks)

        # ── Step 4: Finalize ──
        doc.status = DocumentStatus.COMPLETED
        doc.processed_at = timezone.now()
        doc.total_chunks = len(chunks)
        doc.processing_error = ""
        doc.save(update_fields=["status", "processed_at", "total_chunks", "processing_error"])
        logger.info("Ingestion complete for document: %s (%d chunks)", doc.title, len(chunks))

    except Exception as exc:
        logger.exception("Document processing failed for %s: %s", document_id, exc)
        doc.status = DocumentStatus.FAILED
        doc.processing_error = str(exc)[:2000]
        doc.save(update_fields=["status", "processing_error"])
        if hasattr(self, "request") and getattr(self.request, "retries", 0) < getattr(self, "max_retries", 3) and not getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            raise self.retry(exc=exc)


def _update_status(doc, status: str):
    doc.status = status
    doc.save(update_fields=["status"])


def _parse_document(doc) -> dict:
    """Parse document file using unified DocumentParser."""
    from rag.chunker import DocumentParser
    parser = DocumentParser()
    return parser.parse(doc.file_path, doc.file_name, doc.mime_type)


def _chunk_document(doc, parsed_content: dict) -> list[dict]:
    """
    Apply chunking strategy and preserve all 11 required metadata fields on every chunk:
    - document_id
    - scheme_id
    - scheme_name
    - ministry
    - department
    - state
    - category
    - section
    - page_number
    - source_url
    - document_version
    """
    from rag.chunker import DocumentChunker
    from django.conf import settings

    chunk_size = getattr(settings, "RAG_CHUNK_SIZE", 512)
    chunk_overlap = getattr(settings, "RAG_CHUNK_OVERLAP", 64)

    chunker = DocumentChunker(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        strategy=doc.chunking_strategy,
    )

    scheme_name = doc.scheme.name if doc.scheme else (doc.title or "")
    scheme_id = str(doc.scheme.id) if doc.scheme else None

    base_metadata = {
        "document_id": str(doc.id),
        "scheme_id": scheme_id,
        "scheme_name": scheme_name,
        "ministry": doc.ministry or "",
        "department": doc.department or "",
        "state": doc.state or "",
        "category": doc.category or "",
        "section": "General",
        "source_url": doc.source_url or "",
        "document_version": doc.document_version or "1.0",
        "language": doc.language or "en",
    }

    return chunker.chunk(parsed_content, metadata=base_metadata)


def _embed_and_store_chunks(doc, chunks: list[dict]):
    """Generate embeddings for chunks and store in DocumentChunk model."""
    from rag.embedder import EmbeddingService
    from apps.documents.models import DocumentChunk
    from core.utils import chunk_list

    # Delete existing chunks if re-processing
    DocumentChunk.objects.filter(document=doc).delete()

    embedder = EmbeddingService()
    batch_size = 32

    total_tokens = 0

    for batch_idx, batch in enumerate(chunk_list(chunks, batch_size)):
        texts = [c["content"] for c in batch]
        embeddings = embedder.embed_batch(texts)

        chunk_objects = []
        for i, (chunk_data, embedding) in enumerate(zip(batch, embeddings)):
            global_idx = batch_idx * batch_size + i
            meta = chunk_data.get("metadata", {}).copy()
            meta["embedding"] = embedding  # Keep embedding in metadata JSON for portability

            chunk_obj = DocumentChunk(
                document=doc,
                chunk_index=global_idx,
                content=chunk_data["content"],
                chunk_type=chunk_data.get("chunk_type", "TEXT"),
                page_number=chunk_data.get("page_number"),
                section_title=chunk_data.get("section_title", ""),
                token_count=chunk_data.get("token_count", 0),
                char_count=len(chunk_data["content"]),
                metadata=meta,
            )
            chunk_objects.append(chunk_obj)
            total_tokens += chunk_data.get("token_count", 0)

        # Bulk create chunks
        DocumentChunk.objects.bulk_create(chunk_objects)
        logger.debug("Stored batch %d: %d chunks for doc %s", batch_idx, len(batch), doc.id)

    doc.total_tokens = total_tokens
    doc.save(update_fields=["total_tokens"])
