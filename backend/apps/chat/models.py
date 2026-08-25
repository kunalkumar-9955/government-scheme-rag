"""
apps/chat/models.py — Conversation, Message, and Citation models
"""
import uuid
from django.db import models
from django.conf import settings


class Conversation(models.Model):
    """A chat session between a user and the AI assistant."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations",
        db_index=True,
    )
    title = models.CharField(max_length=300, blank=True, help_text="Auto-generated from first message")
    user_context_snapshot = models.JSONField(
        default=dict,
        blank=True,
        help_text="Snapshot of user profile at conversation start",
    )
    message_count = models.IntegerField(default=0)
    last_message_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_archived = models.BooleanField(default=False)

    class Meta:
        db_table = "conversations"
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["user", "is_archived"]),
            models.Index(fields=["updated_at"]),
        ]

    def __str__(self):
        return f"Conversation {self.id} — {self.user.email}"


class MessageRole(models.TextChoices):
    USER = "user", "User"
    ASSISTANT = "assistant", "Assistant"
    SYSTEM = "system", "System"


class Message(models.Model):
    """A single message in a conversation (user query or AI response)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
        db_index=True,
    )
    role = models.CharField(max_length=10, choices=MessageRole.choices)
    content = models.TextField()

    # RAG metadata (only for assistant messages)
    retrieved_chunks = models.JSONField(
        default=list,
        blank=True,
        help_text="List of retrieved chunk dicts used for this response",
    )
    cited_sources = models.JSONField(
        default=list,
        blank=True,
        help_text="Formatted citations for this response",
    )
    query_type = models.CharField(
        max_length=20,
        blank=True,
        help_text="Classified query intent: eligibility/information/discovery/procedure",
    )
    confidence_score = models.FloatField(null=True, blank=True)
    latency_ms = models.IntegerField(null=True, blank=True)

    # Quality tracking
    feedback_rating = models.IntegerField(null=True, blank=True)  # 1-5 stars
    is_flagged = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "messages"
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "role"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"[{self.role}] in {self.conversation_id}"


class MessageFeedback(models.Model):
    """User feedback on a specific AI message."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.OneToOneField(
        Message,
        on_delete=models.CASCADE,
        related_name="feedback",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="message_feedbacks",
    )
    rating = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    feedback_type = models.CharField(
        max_length=20,
        choices=[
            ("HELPFUL", "Helpful"),
            ("INACCURATE", "Inaccurate"),
            ("INCOMPLETE", "Incomplete"),
            ("CONFUSING", "Confusing"),
            ("OUTDATED", "Outdated"),
            ("OTHER", "Other"),
        ],
        blank=True,
    )
    comment = models.TextField(blank=True, max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "message_feedback"
        verbose_name = "Message Feedback"
        ordering = ["-created_at"]
