from django.conf import settings
from django.db import models


class WorkItem(models.Model):
    """Work the AI surfaced for a human to decide on. Nothing is auto-actioned."""
    CATEGORY = [("CERT", "Certification"), ("UNCOVERED", "Visite non couverte"),
                ("UNSIGNED", "Rapport non signe"), ("HOURS", "Heures a approuver"),
                ("INVOICE", "Facture en retard"), ("FOLLOWUP", "Relance client"), ("OTHER", "Autre")]
    PRIORITY = [("HIGH", "Haute"), ("MEDIUM", "Moyenne"), ("LOW", "Basse")]
    STATUS = [("OPEN", "A traiter"), ("SNOOZED", "Reporte"),
              ("RESOLVED", "Traite"), ("DISMISSED", "Ignore")]

    source_key = models.CharField(max_length=255, unique=True, db_index=True)
    category = models.CharField(max_length=20, choices=CATEGORY)
    priority = models.CharField(max_length=10, choices=PRIORITY, default="MEDIUM")
    status = models.CharField(max_length=10, choices=STATUS, default="OPEN", db_index=True)
    title = models.CharField(max_length=200)
    detail = models.TextField(blank=True)
    link = models.CharField(max_length=300, blank=True)  # where to act
    due_at = models.DateTimeField(null=True, blank=True)
    snooze_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="resolved_items")
    resolved_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(blank=True)

    class Meta:
        ordering = ["-priority", "due_at", "-created_at"]

    def __str__(self):
        return self.title


class WorkItemEvent(models.Model):
    item = models.ForeignKey(WorkItem, on_delete=models.CASCADE, related_name="events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=30)
    note = models.TextField(blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-at"]


class Meeting(models.Model):
    STATUS = [("REQUESTED", "Demandee"), ("CONFIRMED", "Confirmee"),
              ("DECLINED", "Refusee"), ("DONE", "Terminee"), ("CANCELLED", "Annulee")]
    title = models.CharField(max_length=200)
    purpose = models.TextField(blank=True)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                     related_name="meetings_requested")
    client = models.ForeignKey("clients.Client", null=True, blank=True, on_delete=models.SET_NULL,
                               related_name="meetings")
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, through="MeetingParticipant",
                                          related_name="meetings")
    proposed_at = models.DateTimeField()
    duration_min = models.PositiveIntegerField(default=30)
    location = models.CharField(max_length=200, blank=True, help_text="Salle ou lien visio")
    status = models.CharField(max_length=10, choices=STATUS, default="REQUESTED")
    room_token = models.CharField(max_length=24, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["proposed_at"]

    def save(self, *args, **kwargs):
        if not self.room_token:
            import secrets
            self.room_token = secrets.token_hex(8)
        super().save(*args, **kwargs)

    @property
    def video_room(self):
        return f"PantherCare-{self.id}-{self.room_token}"

    def __str__(self):
        return f"{self.title} — {self.proposed_at:%d/%m %H:%M}"


class MeetingParticipant(models.Model):
    RESPONSE = [("PENDING", "En attente"), ("ACCEPTED", "Accepte"), ("DECLINED", "Refuse")]
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name="responses")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    response = models.CharField(max_length=10, choices=RESPONSE, default="PENDING")
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("meeting", "user")


class MeetingMessage(models.Model):
    """In-room text chat for a meeting."""
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name="messages")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    text = models.TextField()
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["at"]
