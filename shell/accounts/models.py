from django.conf import settings
from django.db import models


class AskRecord(models.Model):
    """One row per /ask attempt, success or not — a history that only
    records successes can't show the system being honest about refusing.
    sources and tool_calls are JSON because their shape is owned by the
    engine and will change again; refused/latency_s/error are real columns
    because the trust dashboard aggregates over them."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="asks"
    )
    question = models.TextField()
    answer = models.TextField(blank=True, default="")
    refused = models.BooleanField(default=False)
    latency_s = models.FloatField(null=True, blank=True)
    sources = models.JSONField(default=list, blank=True)
    tool_calls = models.JSONField(default=list, blank=True)
    error = models.CharField(max_length=32, blank=True, default="")
    error_detail = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} · {self.question[:50]}"


class Document(models.Model):
    """One row per document a user owns — the library renders from this,
    never by scanning Qdrant. Qdrant holds vectors; this holds what the
    user owns. Status can express failure (a scanned PDF needing OCR is
    the blueprint's example) as well as the pending/processing states
    upload will need — that detection logic is upload's job, not this
    model's; the states just need to already exist for it to write into."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="documents"
    )
    doc_id = models.CharField(max_length=200)
    display_name = models.CharField(max_length=255)
    page_count = models.IntegerField(null=True, blank=True)
    chunk_count = models.IntegerField(null=True, blank=True)
    figure_count = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    failure_reason = models.TextField(blank=True, default="")
    ingested_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "doc_id"], name="unique_user_doc_id"),
        ]

    def __str__(self):
        return f"{self.user} · {self.doc_id}"
