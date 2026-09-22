from django.db import models
from django.utils import timezone


class VisitStatus(models.TextChoices):
    UNCOVERED = "UNCOVERED", "Non couverte"
    SCHEDULED = "SCHEDULED", "Planifiée"
    IN_PROGRESS = "IN_PROGRESS", "En cours"
    COMPLETED = "COMPLETED", "Terminée"
    MISSED = "MISSED", "Manquée"
    CANCELLED = "CANCELLED", "Annulée"


class Visit(models.Model):
    """A single scheduled care visit. Attendance (GPS check-in/out) is recorded inline."""
    client = models.ForeignKey("clients.Client", on_delete=models.CASCADE, related_name="visits")
    caregiver = models.ForeignKey(
        "caregivers.Caregiver", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="visits",
    )
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    status = models.CharField(max_length=12, choices=VisitStatus.choices, default=VisitStatus.SCHEDULED)

    # Attendance / EVV (Electronic Visit Verification)
    check_in_at = models.DateTimeField(null=True, blank=True)
    check_out_at = models.DateTimeField(null=True, blank=True)
    hours_approved = models.BooleanField(default=False)  # verified hours ready for payroll
    check_in_lat = models.FloatField(null=True, blank=True)
    check_in_lng = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["scheduled_start"]
        indexes = [models.Index(fields=["status", "scheduled_start"])]

    def __str__(self):
        who = self.caregiver.code if self.caregiver else "—"
        return f"{self.client.code} × {who} @ {timezone.localtime(self.scheduled_start):%d %b %H:%M}"

    @property
    def is_uncovered(self):
        return self.caregiver is None or self.status == VisitStatus.UNCOVERED

    @property
    def minutes_late(self):
        """Minutes past the scheduled start with no check-in yet (0 if fine or done)."""
        if self.status in (VisitStatus.COMPLETED, VisitStatus.CANCELLED) or self.check_in_at:
            return 0
        delta = (timezone.now() - self.scheduled_start).total_seconds() / 60
        return int(delta) if delta > 0 else 0

    def check_in(self, lat=None, lng=None):
        self.check_in_at = timezone.now()
        self.check_in_lat, self.check_in_lng = lat, lng
        self.status = VisitStatus.IN_PROGRESS
        self.save(update_fields=["check_in_at", "check_in_lat", "check_in_lng", "status"])

    def check_out(self):
        self.check_out_at = timezone.now()
        self.status = VisitStatus.COMPLETED
        self.save(update_fields=["check_out_at", "status"])


class RequestStatus(models.TextChoices):
    PENDING = "PENDING", "En attente d'approbation"
    APPROVED = "APPROVED", "Approuvée"
    DENIED = "DENIED", "Refusée"


class VisitRequest(models.Model):
    """A caregiver's self-service request to cover an open (unfilled) visit.

    Not a first-come-first-served scheduler: the office reviews each request and makes
    the final decision, prioritising consistency and continuity of care.
    """
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name="requests")
    caregiver = models.ForeignKey("caregivers.Caregiver", on_delete=models.CASCADE,
                                  related_name="visit_requests")
    status = models.CharField(max_length=10, choices=RequestStatus.choices,
                              default=RequestStatus.PENDING)
    score = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["visit", "caregiver"],
                                    name="uniq_visit_caregiver_request"),
        ]

    def __str__(self):
        return f"{self.caregiver.code} → {self.visit} ({self.get_status_display()})"


class RecurringSchedule(models.Model):
    """A 'master week' — a repeating visit pattern that generates individual visits.

    Lets schedulers set up a client's recurring visits (e.g. Mon/Wed/Fri at 09:00 for
    the next 4 weeks) in one step instead of creating each visit by hand.
    """
    WEEKDAYS = [("0", "Lun"), ("1", "Mar"), ("2", "Mer"), ("3", "Jeu"),
                ("4", "Ven"), ("5", "Sam"), ("6", "Dim")]

    client = models.ForeignKey("clients.Client", on_delete=models.CASCADE,
                               related_name="recurring_schedules")
    caregiver = models.ForeignKey("caregivers.Caregiver", null=True, blank=True,
                                  on_delete=models.SET_NULL, related_name="recurring_schedules")
    weekdays = models.CharField(max_length=20, help_text="Comma-separated 0=Mon … 6=Sun")
    start_time = models.TimeField()
    duration_minutes = models.PositiveIntegerField(default=120)
    start_date = models.DateField()
    weeks = models.PositiveSmallIntegerField(default=4)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def weekday_list(self):
        labels = dict(self.WEEKDAYS)
        return [labels[d] for d in self.weekdays.split(",") if d in labels]

    def generate(self):
        """Create the individual Visit rows for this pattern. Returns the count made."""
        from datetime import datetime, timedelta
        from django.utils import timezone
        days = [int(d) for d in self.weekdays.split(",") if d.strip().isdigit()]
        made = 0
        for wk in range(self.weeks):
            monday = self.start_date + timedelta(weeks=wk) - timedelta(days=self.start_date.weekday())
            for wd in days:
                d = monday + timedelta(days=wd)
                if d < self.start_date:
                    continue
                naive = datetime.combine(d, self.start_time)
                start = timezone.make_aware(naive, timezone.get_current_timezone())
                end = start + timedelta(minutes=self.duration_minutes)
                if Visit.objects.filter(client=self.client, scheduled_start=start).exists():
                    continue
                Visit.objects.create(
                    client=self.client, caregiver=self.caregiver,
                    scheduled_start=start, scheduled_end=end,
                    status=VisitStatus.SCHEDULED if self.caregiver else VisitStatus.UNCOVERED)
                made += 1
        return made

    def __str__(self):
        return f"{self.client.code} · {', '.join(self.weekday_list())} · {self.start_time:%H:%M}"
