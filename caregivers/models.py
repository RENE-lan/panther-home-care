import uuid
from django.conf import settings
from django.db import models


class Skill(models.Model):
    """A care competency used by the matching engine (e.g. 'Personnes âgées', 'Démence')."""
    name = models.CharField(max_length=120, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Caregiver(models.Model):
    code = models.CharField(max_length=20, unique=True, help_text="e.g. Soignant #027")
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="caregiver_profile",
    )
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    phone = models.CharField(max_length=32, blank=True)
    languages = models.CharField(max_length=200, blank=True, help_text="Comma-separated")
    skills = models.ManyToManyField(Skill, blank=True, related_name="caregivers")
    home_latitude = models.FloatField(null=True, blank=True)
    home_longitude = models.FloatField(null=True, blank=True)
    # Performance signals feed the reliability score used in AI recommendations.
    reliability_score = models.PositiveSmallIntegerField(default=90, help_text="0–100")
    punctuality_score = models.PositiveSmallIntegerField(default=90)
    weekly_hours_cap = models.PositiveSmallIntegerField(default=45)
    # Preference / attribute matching (feeds the open-visit match score)
    gender = models.CharField(max_length=1, default="U",
                              choices=[("U", "Non précisé"), ("F", "Femme"), ("M", "Homme")])
    comfortable_with_pets = models.BooleanField("à l'aise avec les animaux", default=True)
    comfortable_with_smoking = models.BooleanField("à l'aise en foyer fumeur", default=True)
    pay_rate = models.DecimalField("taux horaire ($)", max_digits=7, decimal_places=2, default=5)
    calendar_token = models.CharField(max_length=36, db_index=True, default=uuid.uuid4, editable=False)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def language_list(self):
        return [l.strip() for l in self.languages.split(",") if l.strip()]

    def __str__(self):
        return f"{self.code} — {self.full_name}"


class Certification(models.Model):
    caregiver = models.ForeignKey(Caregiver, on_delete=models.CASCADE, related_name="certifications")
    name = models.CharField(max_length=120)
    issued_on = models.DateField(null=True, blank=True)
    expires_on = models.DateField(null=True, blank=True)

    def is_expired(self):
        from django.utils import timezone
        return bool(self.expires_on and self.expires_on < timezone.localdate())

    def __str__(self):
        return f"{self.name} — {self.caregiver.code}"


class Availability(models.Model):
    """Weekly availability window. weekday: 0=Mon … 6=Sun."""
    caregiver = models.ForeignKey(Caregiver, on_delete=models.CASCADE, related_name="availability")
    weekday = models.PositiveSmallIntegerField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ["weekday", "start_time"]

    def __str__(self):
        return f"{self.caregiver.code} — jour {self.weekday} {self.start_time}-{self.end_time}"


class ApplicationStage(models.TextChoices):
    APPLICATION = "APPLICATION", "Candidature"
    SCREENING = "SCREENING", "Présélection"
    INTERVIEW = "INTERVIEW", "Entretien"
    BACKGROUND = "BACKGROUND", "Vérification"
    ASSESSMENT = "ASSESSMENT", "Évaluation des compétences"
    TRAINING = "TRAINING", "Formation"
    CERTIFIED = "CERTIFIED", "Certifié"
    ACTIVE = "ACTIVE", "Soignant actif"


class Applicant(models.Model):
    """Caregiver Talent Hub: recruitment + training pipeline into an active caregiver."""
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    phone = models.CharField(max_length=32, blank=True)
    stage = models.CharField(max_length=20, choices=ApplicationStage.choices,
                             default=ApplicationStage.APPLICATION)
    notes = models.TextField(blank=True)
    promoted_to = models.OneToOneField(
        Caregiver, null=True, blank=True, on_delete=models.SET_NULL, related_name="from_applicant",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} — {self.get_stage_display()}"


class CaregiverEvaluation(models.Model):
    """A periodic performance evaluation of a caregiver (supervision / quality)."""
    caregiver = models.ForeignKey(Caregiver, on_delete=models.CASCADE, related_name="evaluations")
    period = models.CharField(max_length=40, help_text="ex. T3 2026")
    punctuality = models.PositiveSmallIntegerField(default=4)     # 1–5
    care_quality = models.PositiveSmallIntegerField(default=4)
    communication = models.PositiveSmallIntegerField(default=4)
    professionalism = models.PositiveSmallIntegerField(default=4)
    notes = models.TextField(blank=True)
    evaluator = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def score(self):
        return round((self.punctuality + self.care_quality + self.communication
                      + self.professionalism) / 4 * 20)  # → %

    def __str__(self):
        return f"{self.caregiver.code} · {self.period} · {self.score}%"


class CaregiverDocument(models.Model):
    """A tracked document for a caregiver (ID, contract, reference, certificate…)."""
    class Type(models.TextChoices):
        ID = "ID", "Pièce d'identité"
        CONTRACT = "CONTRACT", "Contrat"
        REFERENCE = "REFERENCE", "Référence"
        CERTIFICATE = "CERTIFICATE", "Certificat"
        MEDICAL = "MEDICAL", "Visite médicale"
        OTHER = "OTHER", "Autre"

    class Status(models.TextChoices):
        VALID = "VALID", "Valide"
        PENDING = "PENDING", "En attente"
        EXPIRED = "EXPIRED", "Expiré"

    caregiver = models.ForeignKey(Caregiver, on_delete=models.CASCADE, related_name="documents")
    name = models.CharField(max_length=120)
    doc_type = models.CharField(max_length=12, choices=Type.choices, default=Type.OTHER)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.VALID)
    reference = models.CharField(max_length=120, blank=True)
    expires_on = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.caregiver.code} · {self.name}"
