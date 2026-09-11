from django.contrib import admin
from django.utils import timezone

from dashboard.admin_helpers import badge, export_csv
from .models import Incident, IncidentStatus


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ("title", "client", "severity_badge", "status_badge", "created_at")
    list_filter = ("severity", "status")
    search_fields = ("title", "client__code")
    date_hierarchy = "created_at"
    autocomplete_fields = ("client", "caregiver")
    list_per_page = 25
    actions = [export_csv, "mark_resolved", "mark_escalated"]

    @admin.display(description="Gravité", ordering="severity")
    def severity_badge(self, obj):
        return badge(obj.get_severity_display(), obj.severity)

    @admin.display(description="Statut", ordering="status")
    def status_badge(self, obj):
        return badge(obj.get_status_display(), obj.status)

    @admin.action(description="Marquer comme résolu")
    def mark_resolved(self, request, queryset):
        n = queryset.update(status=IncidentStatus.RESOLVED)
        self.message_user(request, f"{n} incident(s) résolu(s).")

    @admin.action(description="Escalader")
    def mark_escalated(self, request, queryset):
        n = queryset.update(status=IncidentStatus.ESCALATED)
        self.message_user(request, f"{n} incident(s) escaladé(s).")
