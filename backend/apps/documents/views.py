"""
apps/documents/views.py — Government document management API
"""
import os
import logging
from pathlib import Path
from django.conf import settings
from django.utils import timezone
from rest_framework import status, filters
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from django_filters.rest_framework import DjangoFilterBackend

from core.permissions import IsAdmin
from core.utils import hash_file, sanitize_filename, success_response
from core.pagination import LargeResultsPagination, StandardResultsPagination
from .models import GovDocument, DocumentChunk, DocumentStatus
from .serializers import (
    DocumentUploadSerializer,
    DocumentSerializer,
    DocumentListSerializer,
    DocumentChunkSerializer,
    DocumentStatusSerializer,
)
from .tasks import process_document

logger = logging.getLogger(__name__)


class DocumentUploadView(APIView):
    """
    POST /api/v1/documents/upload/ — Upload a new government document (PDF/DOCX/HTML/TXT).
    Performs file validation, duplicate hash detection, secure storage, and triggers async ingestion.
    """
    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        file = serializer.validated_data["file"]
        file_hash = hash_file(file)

        # 1. Deduplication check via SHA-256 hash
        existing_doc = GovDocument.objects.filter(file_hash=file_hash).first()
        if existing_doc:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "DUPLICATE_DOCUMENT",
                        "message": f"This document has already been uploaded as '{existing_doc.title}' (ID: {existing_doc.id}).",
                        "existing_document_id": str(existing_doc.id),
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )

        # 2. Determine secure storage path
        safe_filename = sanitize_filename(file.name)

        # 3. Create document record
        document = GovDocument.objects.create(
            uploaded_by=request.user,
            title=serializer.validated_data["title"],
            scheme=serializer.validated_data.get("scheme"),
            ministry=serializer.validated_data.get("ministry", ""),
            department=serializer.validated_data.get("department", ""),
            state=serializer.validated_data.get("state", ""),
            category=serializer.validated_data.get("category", "OTHER"),
            document_version=serializer.validated_data.get("document_version", "1.0"),
            source_url=serializer.validated_data.get("source_url", ""),
            language=serializer.validated_data.get("language", "en"),
            published_date=serializer.validated_data.get("published_date"),
            description=serializer.validated_data.get("description", ""),
            tags=serializer.validated_data.get("tags", []),
            chunking_strategy=serializer.validated_data.get("chunking_strategy", "recursive"),
            file_name=safe_filename,
            file_size_bytes=file.size,
            mime_type=file.content_type or "application/octet-stream",
            file_hash=file_hash,
            status=DocumentStatus.PENDING,
            embedding_model=getattr(settings, "LLM_EMBEDDING_MODEL", "models/text-embedding-004"),
        )

        # 4. Save file to storage
        file_storage_path = self._save_file(file, document)
        document.file_path = file_storage_path
        document.save(update_fields=["file_path"])

        # 5. Queue async processing (with synchronous fallback)
        try:
            task = process_document.delay(str(document.id))
            document.celery_task_id = task.id
            document.status = DocumentStatus.PROCESSING
            document.save(update_fields=["celery_task_id", "status"])
        except Exception as e:
            logger.warning("Celery queueing failed, running ingestion synchronously: %s", e)
            process_document(str(document.id))
            document.refresh_from_db()

        logger.info("Document uploaded: %s (id=%s)", document.title, document.id)

        return Response(
            success_response(
                data=DocumentSerializer(document).data,
                message="Document uploaded successfully. Processing started.",
            ),
            status=status.HTTP_201_CREATED,
        )

    def _save_file(self, file, document: GovDocument) -> str:
        """Save uploaded file to local media storage securely."""
        docs_dir = Path(settings.MEDIA_ROOT) / "documents"
        docs_dir.mkdir(parents=True, exist_ok=True)

        unique_filename = f"{document.id}_{document.file_name}"
        dest_path = docs_dir / unique_filename

        file.seek(0)
        with open(dest_path, "wb") as f:
            for chunk in file.chunks():
                f.write(chunk)
        file.seek(0)

        # Return relative path from MEDIA_ROOT
        return os.path.relpath(dest_path, settings.MEDIA_ROOT)


class DocumentListView(ListAPIView):
    """GET /api/v1/documents/ — List all uploaded government documents."""
    permission_classes = [IsAdmin]
    serializer_class = DocumentListSerializer
    pagination_class = StandardResultsPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "category", "ministry", "state"]
    search_fields = ["title", "ministry", "department", "file_name"]
    ordering_fields = ["uploaded_at", "title", "total_chunks"]
    ordering = ["-uploaded_at"]

    def get_queryset(self):
        return GovDocument.objects.select_related("scheme", "uploaded_by").all()


class DocumentDetailView(APIView):
    """GET/DELETE /api/v1/documents/<doc_id>/ — View details or delete document."""
    permission_classes = [IsAdmin]

    def get(self, request, doc_id):
        try:
            doc = GovDocument.objects.select_related("scheme", "uploaded_by").get(id=doc_id)
        except GovDocument.DoesNotExist:
            return Response(
                {"success": False, "error": {"code": "NOT_FOUND", "message": "Document not found"}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(success_response(data=DocumentSerializer(doc).data))

    def delete(self, request, doc_id):
        try:
            doc = GovDocument.objects.get(id=doc_id)
        except GovDocument.DoesNotExist:
            return Response(
                {"success": False, "error": {"code": "NOT_FOUND", "message": "Document not found"}},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Remove physical file if exists
        try:
            file_full_path = Path(settings.MEDIA_ROOT) / doc.file_path
            if file_full_path.exists():
                file_full_path.unlink()
        except Exception as e:
            logger.warning("Could not delete file %s: %s", doc.file_path, e)

        doc.delete()
        return Response(success_response(message="Document and all associated chunks deleted successfully."))


class DocumentStatusView(APIView):
    """GET /api/v1/documents/<doc_id>/status/ — Polling endpoint for ingestion progress."""
    permission_classes = [IsAdmin]

    def get(self, request, doc_id):
        try:
            doc = GovDocument.objects.get(id=doc_id)
        except GovDocument.DoesNotExist:
            return Response(
                {"success": False, "error": {"code": "NOT_FOUND", "message": "Document not found"}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(success_response(data=DocumentStatusSerializer(doc).data))


class DocumentReprocessView(APIView):
    """POST /api/v1/documents/<doc_id>/reprocess/ — Re-trigger ingestion pipeline."""
    permission_classes = [IsAdmin]

    def post(self, request, doc_id):
        try:
            doc = GovDocument.objects.get(id=doc_id)
        except GovDocument.DoesNotExist:
            return Response(
                {"success": False, "error": {"code": "NOT_FOUND", "message": "Document not found"}},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not doc.can_reprocess:
            return Response(
                {"success": False, "error": {"code": "INVALID_STATE", "message": "Document is currently processing."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        doc.status = DocumentStatus.PENDING
        doc.processing_error = ""
        doc.save(update_fields=["status", "processing_error"])

        try:
            task = process_document.delay(str(doc.id))
            doc.celery_task_id = task.id
            doc.save(update_fields=["celery_task_id"])
        except Exception:
            process_document(str(doc.id))
            doc.refresh_from_db()

        return Response(success_response(data=DocumentSerializer(doc).data, message="Reprocessing started."))


class DocumentChunksView(ListAPIView):
    """GET /api/v1/documents/<doc_id>/chunks/ — Inspect generated chunks and metadata."""
    permission_classes = [IsAdmin]
    serializer_class = DocumentChunkSerializer
    pagination_class = LargeResultsPagination

    def get_queryset(self):
        doc_id = self.kwargs.get("doc_id")
        return DocumentChunk.objects.filter(document_id=doc_id).order_by("chunk_index")


class GlobalChunkListView(ListAPIView):
    """GET /api/v1/documents/chunks/ — Admin global search & inspector for RAG chunks."""
    permission_classes = [IsAdmin]
    serializer_class = DocumentChunkSerializer
    pagination_class = StandardResultsPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["document", "chunk_type"]
    search_fields = ["content", "section_title", "keywords"]

    def get_queryset(self):
        return DocumentChunk.objects.select_related("document").order_by("-created_at")
