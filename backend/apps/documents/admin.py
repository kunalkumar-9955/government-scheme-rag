"""
apps/documents/admin.py — Django Admin configuration for GovDocument & DocumentChunk
"""
from django.contrib import admin
from .models import GovDocument, DocumentChunk


class DocumentChunkInline(admin.TabularInline):
    model = DocumentChunk
    extra = 0
    fields = ("chunk_index", "chunk_type", "page_number", "section_title", "token_count")
    readonly_fields = ("chunk_index", "chunk_type", "page_number", "section_title", "token_count")
    can_delete = False
    show_change_link = True


@admin.register(GovDocument)
class GovDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "ministry",
        "category",
        "status",
        "total_chunks",
        "page_count",
        "document_version",
        "uploaded_at",
    )
    list_filter = ("status", "category", "language", "chunking_strategy")
    search_fields = ("title", "ministry", "department", "file_name")
    readonly_fields = (
        "id",
        "file_hash",
        "file_size_bytes",
        "mime_type",
        "total_chunks",
        "total_tokens",
        "page_count",
        "celery_task_id",
        "uploaded_at",
        "processed_at",
        "updated_at",
    )
    inlines = [DocumentChunkInline]


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ("document", "chunk_index", "chunk_type", "page_number", "section_title", "token_count")
    list_filter = ("chunk_type",)
    search_fields = ("content", "section_title", "document__title")
    readonly_fields = ("id", "document", "chunk_index", "token_count", "char_count", "created_at")
