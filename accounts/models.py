from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    MANAGER = "MANAGER", "Manager (accès complet)"
    ADMIN = "ADMIN", "Administrateur"
    COORDINATOR = "COORDINATOR", "Coordinateur"
    SUPERVISOR = "SUPERVISOR", "Superviseur"
    FINANCE = "FINANCE", "Financier"
    CAREGIVER = "CAREGIVER", "Soignant"
    FAMILY = "FAMILY", "Famille / Client"
    CLINICAL = "CLINICAL", "Conseiller clinique"


class User(AbstractUser):
    """One user table for every portal; the role decides which portal they land in."""
    email = models.EmailField("adresse e-mail", unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.COORDINATOR)
    phone = models.CharField(max_length=32, blank=True)
    id_number = models.CharField("numéro d'identification", max_length=40, blank=True,
                                 db_index=True, help_text="Identifiant unique de connexion")
    mfa_enabled = models.BooleanField(default=False)

    @property
    def is_coordinator(self):
        return self.role in (Role.COORDINATOR, Role.ADMIN)

    @property
    def is_caregiver(self):
        return self.role == Role.CAREGIVER

    @property
    def is_family(self):
        return self.role == Role.FAMILY

    # ---- Role-based access: each role sees only its area ----
    @property
    def is_full_access(self):
        return self.is_superuser or self.role in (Role.MANAGER, Role.ADMIN)

    @property
    def is_office(self):
        return self.is_staff or self.role in (
            Role.MANAGER, Role.ADMIN, Role.COORDINATOR, Role.SUPERVISOR,
            Role.FINANCE, Role.CLINICAL)

    @property
    def can_ops(self):
        return self.is_full_access or self.role in (Role.COORDINATOR, Role.SUPERVISOR)

    @property
    def can_care(self):
        return self.is_full_access or self.role in (Role.COORDINATOR, Role.SUPERVISOR, Role.CLINICAL)

    @property
    def can_schedule(self):
        return self.is_full_access or self.role in (Role.COORDINATOR, Role.SUPERVISOR)

    @property
    def can_finance(self):
        return self.is_full_access or self.role in (Role.COORDINATOR, Role.FINANCE)

    @property
    def can_crm(self):
        return self.is_full_access or self.role == Role.COORDINATOR

    @property
    def can_analytics(self):
        return self.is_full_access or self.role in (
            Role.COORDINATOR, Role.SUPERVISOR, Role.FINANCE, Role.CLINICAL)

    @property
    def can_admin(self):
        """Manage users, settings, automations — manager/admin only."""
        return self.is_full_access

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"


class TimeEntry(models.Model):
    """Staff time-clock entry: a sign-in (clock-in) and sign-out (clock-out).

    Staff punch in/out to record work hours; coordinators/admins can adjust the
    recorded times (e.g. a forgotten clock-out). Fully visible in the Django admin.
    """
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="time_entries")
    clock_in = models.DateTimeField()
    clock_out = models.DateTimeField(null=True, blank=True)
    note = models.CharField(max_length=200, blank=True)
    adjusted = models.BooleanField(default=False)
    adjusted_by = models.ForeignKey("accounts.User", null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="time_adjustments")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-clock_in"]
        verbose_name = "pointage"
        verbose_name_plural = "pointages"

    @property
    def is_open(self):
        return self.clock_out is None

    @property
    def hours(self):
        if self.clock_out:
            return round((self.clock_out - self.clock_in).total_seconds() / 3600, 2)
        return None

    def __str__(self):
        return f"{self.user} · {self.clock_in:%d/%m %H:%M}"


class AgencySettings(models.Model):
    """Singleton configuration that actually drives Panther (EVV, automations, billing,
    notifications). Load with AgencySettings.get()."""
    # Agency
    agency_name = models.CharField(max_length=120, default="Panther Home Care")
    address = models.CharField(max_length=200, blank=True, default="Lubumbashi, RDC")
    contact_email = models.EmailField(blank=True, default="contact@panthergroup.cd")
    contact_phone = models.CharField(max_length=40, blank=True)
    currency = models.CharField(max_length=6, default="$")
    business_hours = models.CharField(max_length=60, default="08:00 – 18:00")
    default_visit_minutes = models.PositiveIntegerField(default=120)
    # EVV
    late_threshold_min = models.PositiveIntegerField("seuil de retard (min)", default=15)
    geofence_km = models.DecimalField(max_digits=4, decimal_places=1, default=1.0)
    require_gps = models.BooleanField(default=True)
    # Scheduling
    max_weekly_hours = models.PositiveIntegerField(default=45)
    max_travel_km = models.PositiveIntegerField(default=25)
    auto_replacement = models.BooleanField("recherche auto de remplaçant", default=True)
    # Billing
    default_bill_rate = models.DecimalField(max_digits=7, decimal_places=2, default=8)
    default_pay_rate = models.DecimalField(max_digits=7, decimal_places=2, default=5)
    payment_terms_days = models.PositiveIntegerField(default=15)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    invoice_prefix = models.CharField(max_length=10, default="INV")
    # AI & Automation
    automation_enabled = models.BooleanField(default=True)
    ai_auto_fill = models.BooleanField("l'IA peut affecter automatiquement", default=False)
    ai_confidence_threshold = models.PositiveIntegerField("seuil de confiance IA (%)", default=80)
    # Notifications
    notify_email = models.BooleanField(default=True)
    notify_sms = models.BooleanField(default=False)
    alert_late = models.BooleanField(default=True)
    alert_missed = models.BooleanField(default=True)
    alert_incident = models.BooleanField(default=True)
    alert_cert = models.BooleanField(default=True)
    alert_billing = models.BooleanField(default=True)

    class Meta:
        verbose_name = "paramètres de l'agence"
        verbose_name_plural = "paramètres de l'agence"

    def __str__(self):
        return self.agency_name

    @classmethod
    def get(cls):
        obj = cls.objects.first()
        if obj is None:
            obj = cls.objects.create()
        return obj
