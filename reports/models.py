from django.db import models


class Mood(models.IntegerChoices):
    VERY_GOOD = 5, "Très bien"
    GOOD = 4, "Bien"
    NEUTRAL = 3, "Neutre"
    LOW = 2, "Bas"
    BAD = 1, "Mauvais"


class CareReport(models.Model):
    """A caregiver's report after a visit. AI scans it for potential concerns."""
    visit = models.OneToOneField("scheduling.Visit", on_delete=models.CASCADE, related_name="report")
    caregiver = models.ForeignKey("caregivers.Caregiver", null=True, on_delete=models.SET_NULL)
    notes = models.TextField(blank=True)
    mood = models.PositiveSmallIntegerField(choices=Mood.choices, default=Mood.NEUTRAL)
    blood_pressure = models.CharField(max_length=20, blank=True, help_text="e.g. 120/80")
    pulse = models.CharField(max_length=20, blank=True, help_text="bpm")
    tasks_completed = models.JSONField(default=list, blank=True)

    # Populated by the AI risk pass — never a diagnosis, only a flag for human review.
    ai_flagged = models.BooleanField(default=False)
    ai_concern = models.CharField(max_length=255, blank=True)

    # Care Insights: category + severity of the note (guidance, not a diagnosis).
    insight_category = models.CharField(max_length=12, default="GENERAL", choices=[
        ("MEDICAL", "Médical"), ("CLINICAL", "Clinique"),
        ("FUNCTIONAL", "Fonctionnel"), ("GENERAL", "Général")])
    insight_severity = models.PositiveSmallIntegerField(default=0)  # 0 none … 3 high

    # Digital signature — the caregiver signs to confirm the visit/note.
    signature = models.TextField(blank=True)   # data-URL PNG of the drawn signature
    signed_by = models.CharField(max_length=120, blank=True)
    signed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Rapport — {self.visit.client.code} @ {self.created_at:%d %b %H:%M}"


def _sig_upload(instance, filename):
    return f"signatures/{instance.pk or 'new'}.png"
