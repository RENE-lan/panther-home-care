from django.conf import settings
from django.db import models


class RiskLevel(models.TextChoices):
    LOW = "LOW", "Faible"
    MEDIUM = "MEDIUM", "Moyen"
    HIGH = "HIGH", "Élevé"
    CRITICAL = "CRITICAL", "Critique"


class Client(models.Model):
    """A care recipient. Client 360° is assembled from this + related models."""
    code = models.CharField(max_length=20, unique=True, help_text="e.g. Client #014")
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.CharField(max_length=255, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    preferred_language = models.CharField(max_length=40, blank=True)
    care_type = models.CharField(max_length=120, blank=True, help_text="e.g. Personnes âgées")
    risk_level = models.CharField(max_length=10, choices=RiskLevel.choices, default=RiskLevel.LOW)
    # Environment / preference attributes (feed the caregiver match score)
    has_pets = models.BooleanField("présence d'animaux", default=False)
    smoking_household = models.BooleanField("foyer fumeur", default=False)
    caregiver_gender_preference = models.CharField(
        max_length=10, default="ANY",
        choices=[("ANY", "Indifférent"), ("FEMALE", "Soignante (femme)"),
                 ("MALE", "Soignant (homme)")])
    notes = models.TextField(blank=True)
    # Family portal login is linked here.
    family_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="linked_clients",
    )
    bill_rate = models.DecimalField("tarif horaire ($)", max_digits=7, decimal_places=2, default=8)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return f"{self.code} — {self.full_name}"


class EmergencyContact(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="contacts")
    name = models.CharField(max_length=120)
    relationship = models.CharField(max_length=80, blank=True)
    phone = models.CharField(max_length=32)
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.relationship})"


class CarePlan(models.Model):
    """What care a client needs — drives the checklist on each visit and skills matching."""
    client = models.OneToOneField(Client, on_delete=models.CASCADE, related_name="care_plan")
    summary = models.TextField(blank=True)
    required_skills = models.ManyToManyField("caregivers.Skill", blank=True, related_name="care_plans")
    visit_duration_minutes = models.PositiveIntegerField(default=240)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Plan de soins — {self.client.code}"


class CareTask(models.Model):
    """A recurring task the caregiver ticks off each visit (hygiene, medication, meals…)."""
    care_plan = models.ForeignKey(CarePlan, on_delete=models.CASCADE, related_name="tasks")
    label = models.CharField(max_length=120)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.label


class Invoice(models.Model):
    """A client invoice shown transparently in the family portal."""
    class Status(models.TextChoices):
        PAID = "PAID", "Payée"
        DUE = "DUE", "À régler"
        OVERDUE = "OVERDUE", "En retard"

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="invoices")
    period = models.CharField(max_length=40, help_text="e.g. Août 2026")
    hours = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DUE)
    paid_on = models.DateField(null=True, blank=True)
    issued_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-issued_date"]

    def __str__(self):
        return f"{self.client.code} · {self.period} · {self.amount}"


class Message(models.Model):
    """A message between an agency coordinator and a client's family (portal thread)."""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL)
    from_agency = models.BooleanField(default=False)
    body = models.TextField()
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        who = "Agence" if self.from_agency else "Famille"
        return f"{self.client.code} · {who} · {self.created_at:%d/%m %H:%M}"


class CareConcern(models.Model):
    """An ongoing clinical concern for a client (wound, skin, pain, mobility…),
    tracked over time with dated progress updates — the interactive wound/care manager."""
    class Type(models.TextChoices):
        WOUND = "WOUND", "Plaie / escarre"
        SKIN = "SKIN", "Peau"
        PAIN = "PAIN", "Douleur"
        MOBILITY = "MOBILITY", "Mobilité"
        NUTRITION = "NUTRITION", "Nutrition"
        COGNITIVE = "COGNITIVE", "Cognitif"
        OTHER = "OTHER", "Autre"

    class Status(models.TextChoices):
        OPEN = "OPEN", "En cours"
        IMPROVING = "IMPROVING", "En amélioration"
        RESOLVED = "RESOLVED", "Résolue"

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="concerns")
    concern_type = models.CharField(max_length=12, choices=Type.choices, default=Type.WOUND)
    location = models.CharField(max_length=80, blank=True, help_text="ex. talon gauche")
    description = models.TextField(blank=True)
    severity = models.PositiveSmallIntegerField(default=2)  # 1 léger … 3 sévère
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    opened_on = models.DateField(default=None, null=True, blank=True)
    resolved_on = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.client.code} · {self.get_concern_type_display()} ({self.get_status_display()})"


class ConcernUpdate(models.Model):
    """A dated progress note on a care concern (measurement + observation)."""
    concern = models.ForeignKey(CareConcern, on_delete=models.CASCADE, related_name="updates")
    note = models.TextField()
    measurement = models.CharField(max_length=60, blank=True, help_text="ex. 3 cm × 2 cm")
    status = models.CharField(max_length=10, choices=CareConcern.Status.choices,
                              default=CareConcern.Status.OPEN)
    created_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class Lead(models.Model):
    """A prospect / referral before they become a client — the start of the pipeline
    (LEAD → CLIENT → CARE PLAN → SCHEDULE → …)."""
    class Source(models.TextChoices):
        REFERRAL = "REFERRAL", "Recommandation"
        WEB = "WEB", "Site web"
        PHONE = "PHONE", "Téléphone"
        HOSPITAL = "HOSPITAL", "Hôpital / clinique"
        OTHER = "OTHER", "Autre"

    class Stage(models.TextChoices):
        NEW = "NEW", "Nouveau"
        CONTACTED = "CONTACTED", "Contacté"
        ASSESSMENT = "ASSESSMENT", "Évaluation"
        CONVERTED = "CONVERTED", "Converti"
        LOST = "LOST", "Perdu"

    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    source = models.CharField(max_length=12, choices=Source.choices, default=Source.REFERRAL)
    referred_by = models.CharField(max_length=120, blank=True)
    care_need = models.CharField(max_length=120, blank=True)
    stage = models.CharField(max_length=12, choices=Stage.choices, default=Stage.NEW)
    notes = models.TextField(blank=True)
    converted_client = models.ForeignKey(Client, null=True, blank=True,
                                         on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.get_stage_display()})"


class ClientContract(models.Model):
    """Service agreement for a client — hours, rate, dates, status."""
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Brouillon"
        ACTIVE = "ACTIVE", "Actif"
        ENDED = "ENDED", "Terminé"

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="contracts")
    reference = models.CharField(max_length=40, blank=True)
    hours_per_week = models.DecimalField(max_digits=6, decimal_places=1, default=10)
    hourly_rate = models.DecimalField(max_digits=7, decimal_places=2, default=8)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.ACTIVE)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.client.code} · {self.get_status_display()}"


class ClientAssessment(models.Model):
    """Initial / periodic needs assessment — the step between CLIENT and CARE PLAN.
    Captures the evaluation that informs the care plan (mobility, cognition, ADLs,
    fall risk, recommended hours and care type)."""
    class Level(models.TextChoices):
        INDEPENDENT = "INDEPENDENT", "Autonome"
        ASSISTED = "ASSISTED", "Aide partielle"
        DEPENDENT = "DEPENDENT", "Dépendant"

    class Cognition(models.TextChoices):
        NORMAL = "NORMAL", "Normale"
        MILD = "MILD", "Trouble léger"
        MODERATE = "MODERATE", "Trouble modéré"
        SEVERE = "SEVERE", "Trouble sévère"

    class Risk(models.TextChoices):
        LOW = "LOW", "Faible"
        MEDIUM = "MEDIUM", "Moyen"
        HIGH = "HIGH", "Élevé"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Brouillon"
        COMPLETED = "COMPLETED", "Terminée"

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="assessments")
    assessed_on = models.DateField()
    assessor = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL)
    mobility = models.CharField(max_length=12, choices=Level.choices, default=Level.ASSISTED)
    cognition = models.CharField(max_length=10, choices=Cognition.choices, default=Cognition.NORMAL)
    fall_risk = models.CharField(max_length=8, choices=Risk.choices, default=Risk.LOW)
    adl_needs = models.CharField(max_length=300, blank=True, help_text="Comma-separated ADLs")
    medical_notes = models.TextField(blank=True)
    recommended_hours = models.DecimalField(max_digits=6, decimal_places=1, default=10)
    recommended_care_type = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-assessed_on"]

    def adl_list(self):
        return [a.strip() for a in self.adl_needs.split(",") if a.strip()]

    def __str__(self):
        return f"{self.client.code} · {self.assessed_on} ({self.get_status_display()})"
