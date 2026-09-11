from django.contrib import admin

from dashboard.admin_helpers import badge, export_csv
from .models import CarePlan, CareTask, Client, EmergencyContact


class ContactInline(admin.TabularInline):
    model = EmergencyContact
    extra = 0


class TaskInline(admin.TabularInline):
    model = CareTask
    extra = 0


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("code", "full_name", "care_type", "risk_badge", "language", "active")
    list_filter = ("risk_level", "active", "care_type", "preferred_language")
    search_fields = ("code", "first_name", "last_name", "address")
    list_per_page = 25
    inlines = [ContactInline]
    actions = [export_csv]

    @admin.display(description="Risque", ordering="risk_level")
    def risk_badge(self, obj):
        return badge(obj.get_risk_level_display(), obj.risk_level)

    @admin.display(description="Langue")
    def language(self, obj):
        return obj.preferred_language or "—"


@admin.register(CarePlan)
class CarePlanAdmin(admin.ModelAdmin):
    list_display = ("client", "visit_duration_minutes", "updated_at")
    filter_horizontal = ("required_skills",)
    search_fields = ("client__code", "client__first_name", "client__last_name")
    inlines = [TaskInline]


from .models import Invoice, Message


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("client", "period", "hours", "amount", "status", "issued_date")
    list_filter = ("status",)
    search_fields = ("client__code", "period")
    autocomplete_fields = ("client",)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("client", "from_agency", "created_at", "read")
    list_filter = ("from_agency", "read")
    search_fields = ("client__code", "body")
    autocomplete_fields = ("client",)


from .models import Lead


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("name", "source", "stage", "care_need", "created_at")
    list_filter = ("stage", "source")
    search_fields = ("name", "phone", "email", "referred_by")
    date_hierarchy = "created_at"


from .models import ClientContract


@admin.register(ClientContract)
class ClientContractAdmin(admin.ModelAdmin):
    list_display = ("client", "reference", "hours_per_week", "hourly_rate", "status", "start_date")
    list_filter = ("status",)
    search_fields = ("client__code", "reference")
    autocomplete_fields = ("client",)


from .models import ClientAssessment


@admin.register(ClientAssessment)
class ClientAssessmentAdmin(admin.ModelAdmin):
    list_display = ("client", "assessed_on", "mobility", "fall_risk", "recommended_hours", "status")
    list_filter = ("status", "mobility", "fall_risk")
    search_fields = ("client__code",)
    autocomplete_fields = ("client", "assessor")
