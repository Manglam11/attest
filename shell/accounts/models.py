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
