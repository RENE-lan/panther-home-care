from django.contrib import admin

from dashboard.admin_helpers import badge, export_csv
from .models import Visit


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ("client", "caregiver", "scheduled_start", "scheduled_end", "status_badge")
    list_filter = ("status",)
    date_hierarchy = "scheduled_start"
    autocomplete_fields = ("client", "caregiver")
    search_fields = ("client__code", "caregiver__code")
    list_per_page = 30
    actions = [export_csv]

    @admin.display(description="Statut", ordering="status")
    def status_badge(self, obj):
        return badge(obj.get_status_display(), obj.status)


from dashboard.admin_helpers import badge as _badge
from .models import VisitRequest


@admin.register(VisitRequest)
class VisitRequestAdmin(admin.ModelAdmin):
    list_display = ("caregiver", "visit", "score", "status_badge", "created_at")
    list_filter = ("status",)
    search_fields = ("caregiver__code", "visit__client__code")
    date_hierarchy = "created_at"
    autocomplete_fields = ("visit", "caregiver")

    @admin.display(description="Statut", ordering="status")
    def status_badge(self, obj):
        colors = {"PENDING": "MEDIUM", "APPROVED": "RESOLVED", "DENIED": "OPEN"}
        return _badge(obj.get_status_display(), colors.get(obj.status, "OPEN"))


from .models import RecurringSchedule


@admin.register(RecurringSchedule)
class RecurringScheduleAdmin(admin.ModelAdmin):
    list_display = ("client", "caregiver", "start_time", "weeks", "active", "created_at")
    list_filter = ("active",)
    search_fields = ("client__code", "caregiver__code")
    autocomplete_fields = ("client", "caregiver")
