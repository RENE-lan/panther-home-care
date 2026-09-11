from django.conf import settings
from django.db import models


class Severity(models.TextChoices):
    LOW = "LOW", "Faible"
    MEDIUM = "MEDIUM", "Moyen"
    HIGH = "HIGH", "Élevé"
    CRITICAL = "CRITICAL", "Critique"


class IncidentStatus(models.TextChoices):
    OPEN = "OPEN", "Ouvert"
    IN_REVIEW = "IN_REVIEW", "En revue"
    ESCALATED = "ESCALATED", "Escaladé"
    RESOLVED = "RESOLVED", "Résolu"


class Incident(models.Model):
    client = models.ForeignKey("clients.Client", null=True, blank=True,
                               on_delete=models.SET_NULL, related_name="incidents")
    caregiver = models.ForeignKey("caregivers.Caregiver", null=True, blank=True,
                                  on_delete=models.SET_NULL, related_name="incidents")
    visit = models.ForeignKey("scheduling.Visit", null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="incidents")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.LOW)
    status = models.CharField(max_length=12, choices=IncidentStatus.choices, default=IncidentStatus.OPEN)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="assigned_incidents")
    response_due_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_critical(self):
        return self.severity == Severity.CRITICAL

    def __str__(self):
        return f"[{self.get_severity_display()}] {self.title}"
