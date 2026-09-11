from django.contrib import admin

from dashboard.admin_helpers import badge, export_csv
from .models import CareReport


@admin.register(CareReport)
class CareReportAdmin(admin.ModelAdmin):
    list_display = ("visit", "caregiver", "mood", "blood_pressure", "ai_flag_badge", "created_at")
    list_filter = ("ai_flagged", "mood")
    search_fields = ("visit__client__code", "caregiver__code", "ai_concern")
    date_hierarchy = "created_at"
    autocomplete_fields = ("visit", "caregiver")
    list_per_page = 30
    actions = [export_csv]

    @admin.display(description="IA", ordering="ai_flagged")
    def ai_flag_badge(self, obj):
        return badge("Préoccupation", "HIGH") if obj.ai_flagged else badge("RAS", "LOW")
