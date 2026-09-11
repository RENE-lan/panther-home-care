from django.conf import settings
from django.db import models


class AlertLevel(models.TextChoices):
    INFO = "INFO", "Info"
    ATTENTION = "ATTENTION", "Attention"
    CRITICAL = "CRITICAL", "Critique"


class Notification(models.Model):
    """Alert Engine output: EVENT -> rule/AI prioritisation -> notification -> acknowledgement."""
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                  on_delete=models.CASCADE, related_name="notifications")
    level = models.CharField(max_length=10, choices=AlertLevel.choices, default=AlertLevel.INFO)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    link = models.CharField(max_length=300, blank=True)
    read = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.get_level_display()}] {self.title}"
