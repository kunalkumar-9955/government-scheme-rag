"""
apps/documents/models.py — Government document, chunk, and processing models
"""
import uuid
from django.db import models
from django.conf import settings


class DocumentStatus(models.TextChoices):
    PENDING = "PENDING", "Pending Upload"
    PROCESSING = "PROCESSING", "Processing"
    CHUNKING = "CHUNKING", "Chunking"
    EMBEDDING = "EMBEDDING", "Embedding"
    EXTRACTING = "EXTRACTING", "Extracting Schemes"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"


class DocumentCategory(models.TextChoices):
    AGRICULTURE = "AGRICULTURE", "Agriculture"
    EDUCATION = "EDUCATION", "Education"
    HEALTH = "HEALTH", "Health"
    HOUSING = "HOUSING", "Housing"
    SOCIAL_WELFARE = "SOCIAL_WELFARE", "Social Welfare"
    EMPLOYMENT = "EMPLOYMENT", "Employment"
    WOMEN_CHILD = "WOMEN_CHILD", "Women & Child Development"
    SKILL_DEVELOPMENT = "SKILL_DEVELOPMENT", "Skill Development"
    FINANCIAL_INCLUSION = "FINANCIAL_INCLUSION", "Financial Inclusion"
    ENTREPRENEURSHIP = "ENTREPRENEURSHIP", "Entrepreneurship"
    DISABILITY = "DISABILITY", "Disability"
    MINORITY = "MINORITY", "Minority Welfare"
    OTHER = "OTHER", "Other"


class GovDocument(models.Model):
    """
    A government scheme document (PDF/DOCX) uploaded by admins.
    Tracks the full ingestion lifecycle from upload → chunks → embeddings → scheme extraction.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_documents",
    )

    # Document metadata
    title = models.CharField(max_length=500)
    scheme = models.ForeignKey(
        "schemes.GovernmentScheme",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )
    ministry = models.CharField(max_length=300, blank=True, db_index=True)
    department = models.CharField(max_length=300, blank=True)
    state = models.CharField(max_length=100, blank=True, help_text="State / UT if state-specific scheme")
    category = models.CharField(
        max_length=30,
        choices=DocumentCategory.choices,
        default=DocumentCategory.OTHER,
        db_index=True,
    )
    document_version = models.CharField(max_length=50, default="1.0", help_text="Version / revision of the document")
    source_url = models.URLField(max_length=1000, blank=True)
    language = models.CharField(max_length=10, default="en")
    published_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)

    # File storage
    file_path = models.CharField(max_length=1000, blank=True)  # S3 key or local path
    file_name = models.CharField(max_length=500, blank=True)
    file_size_bytes = models.BigIntegerField(null=True, blank=True)
    file_hash = models.CharField(max_length=64, unique=True, db_index=True)  # SHA-256 dedup
    mime_type = models.CharField(max_length=100, blank=True)
    page_count = models.IntegerField(null=True, blank=True)

    # Processing state
    status = models.CharField(
        max_length=20,
        choices=DocumentStatus.choices,
        default=DocumentStatus.PENDING,
        db_index=True,
    )
    processing_error = models.TextField(blank=True)
    total_chunks = models.IntegerField(default=0)
    total_tokens = models.BigIntegerField(default=0)
    celery_task_id = models.CharField(max_length=255, blank=True)

    # Settings used during processing
    chunking_strategy = models.CharField(max_length=50, default="recursive")
    embedding_model = models.CharField(max_length=200, blank=True)

    # Timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "gov_documents"
        verbose_name = "Government Document"
        verbose_name_plural = "Government Documents"
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["status", "category"]),
            models.Index(fields=["ministry"]),
        ]

    def __str__(self):
        return f"{self.title} [{self.status}]"

    @property
    def is_processed(self) -> bool:
        return self.status == DocumentStatus.COMPLETED

    @property
    def can_reprocess(self) -> bool:
        return self.status in [DocumentStatus.COMPLETED, DocumentStatus.FAILED]


class ChunkType(models.TextChoices):
    TEXT = "TEXT", "Text Paragraph"
    TABLE = "TABLE", "Table"
    HEADING = "HEADING", "Heading"
    LIST = "LIST", "List"
    ELIGIBILITY = "ELIGIBILITY", "Eligibility Section"
    BENEFITS = "BENEFITS", "Benefits Section"
    PROCEDURE = "PROCEDURE", "Procedure Section"
    DOCUMENTS = "DOCUMENTS", "Required Documents"


class DocumentChunk(models.Model):
    """
    A single chunk of a government document with its embedding vector.
    Uses pgvector for semantic search.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        GovDocument,
        on_delete=models.CASCADE,
        related_name="chunks",
        db_index=True,
    )

    # Chunk content
    chunk_index = models.IntegerField()
    content = models.TextField()
    chunk_type = models.CharField(
        max_length=20,
        choices=ChunkType.choices,
        default=ChunkType.TEXT,
    )

    # Vector embedding (stored via pgvector)
    # Note: the actual vector field is added via migration using pgvector
    # embedding = VectorField(dimensions=768)  → added in migration

    # Structural metadata
    page_number = models.IntegerField(null=True, blank=True)
    section_title = models.CharField(max_length=500, blank=True)
    heading_path = models.CharField(max_length=1000, blank=True)

    # Token stats
    token_count = models.IntegerField(default=0)
    char_count = models.IntegerField(default=0)

    # Rich metadata for citation and filtering
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="ministry, scheme_name, year, language, etc.",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "document_chunks"
        verbose_name = "Document Chunk"
        verbose_name_plural = "Document Chunks"
        ordering = ["document", "chunk_index"]
        unique_together = [["document", "chunk_index"]]
        indexes = [
            models.Index(fields=["document", "chunk_type"]),
            models.Index(fields=["page_number"]),
        ]

    def __str__(self):
        return f"Chunk {self.chunk_index} of {self.document.title}"
