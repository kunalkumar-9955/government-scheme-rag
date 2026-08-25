"""
apps/documents/serializers.py — Document API serializers
"""
from rest_framework import serializers
from .models import GovDocument, DocumentChunk, DocumentStatus, DocumentCategory
from apps.schemes.models import GovernmentScheme


class DocumentUploadSerializer(serializers.ModelSerializer):
    """For uploading a new government document."""
    file = serializers.FileField(write_only=True)
    scheme = serializers.PrimaryKeyRelatedField(
        queryset=GovernmentScheme.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = GovDocument
        fields = [
            "file", "title", "scheme", "ministry", "department", "state", "category",
            "document_version", "source_url", "language", "published_date",
            "description", "tags", "chunking_strategy",
        ]

    def validate_file(self, value):
        from core.utils import validate_file_extension, validate_file_magic
        from django.conf import settings

        # 1. Extension validation
        if not validate_file_extension(value.name):
            allowed = getattr(
                settings,
                "ALLOWED_DOCUMENT_EXTENSIONS",
                [".pdf", ".docx", ".doc", ".html", ".htm", ".txt"]
            )
            raise serializers.ValidationError(
                f"Unsupported file type. Allowed extensions: {', '.join(allowed)}"
            )

        # 2. File size validation
        max_size_mb = getattr(settings, "MAX_DOCUMENT_SIZE_MB", 50)
        max_size = max_size_mb * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File too large ({value.size / (1024 * 1024):.1f}MB). Maximum allowed size: {max_size_mb}MB."
            )

        # 3. Magic bytes / Anti-malware validation
        is_safe, error_msg = validate_file_magic(value, value.name)
        if not is_safe:
            raise serializers.ValidationError(error_msg)

        return value


class DocumentSerializer(serializers.ModelSerializer):
    """Full document response including processing stats and metadata."""
    uploaded_by_email = serializers.EmailField(source="uploaded_by.email", read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    scheme_name = serializers.CharField(source="scheme.name", read_only=True)
    is_processed = serializers.BooleanField(read_only=True)
    can_reprocess = serializers.BooleanField(read_only=True)

    class Meta:
        model = GovDocument
        fields = [
            "id", "title", "scheme", "scheme_name", "ministry", "department", "state",
            "category", "category_display", "document_version", "source_url", "language",
            "published_date", "description", "tags",
            "file_name", "file_size_bytes", "mime_type", "page_count",
            "status", "status_display", "processing_error",
            "total_chunks", "total_tokens", "chunking_strategy", "embedding_model",
            "uploaded_by_email", "is_processed", "can_reprocess",
            "uploaded_at", "processed_at", "updated_at",
        ]
        read_only_fields = [
            "id", "file_name", "file_size_bytes", "mime_type", "page_count",
            "status", "processing_error", "total_chunks", "total_tokens",
            "embedding_model", "uploaded_at", "processed_at", "updated_at",
        ]


class DocumentListSerializer(serializers.ModelSerializer):
    """Lightweight list serializer."""
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    scheme_name = serializers.CharField(source="scheme.name", read_only=True)

    class Meta:
        model = GovDocument
        fields = [
            "id", "title", "scheme", "scheme_name", "ministry", "department", "state",
            "category", "category_display", "document_version",
            "status", "status_display", "total_chunks", "page_count", "uploaded_at", "processed_at",
        ]


class DocumentChunkSerializer(serializers.ModelSerializer):
    """For viewing chunks of a document (admin)."""
    document_title = serializers.CharField(source="document.title", read_only=True)
    chunk_type_display = serializers.CharField(source="get_chunk_type_display", read_only=True)

    class Meta:
        model = DocumentChunk
        fields = [
            "id", "document", "document_title", "chunk_index", "content",
            "chunk_type", "chunk_type_display", "page_number",
            "section_title", "token_count", "char_count", "metadata", "created_at",
        ]
        read_only_fields = fields


class DocumentStatusSerializer(serializers.ModelSerializer):
    """Polling endpoint — status, page count, chunks, and errors."""
    class Meta:
        model = GovDocument
        fields = ["id", "status", "page_count", "total_chunks", "processing_error", "processed_at", "celery_task_id"]
