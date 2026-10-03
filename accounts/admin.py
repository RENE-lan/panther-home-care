from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class PantherUserAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "role", "is_staff")
    list_filter = ("role", "is_staff", "is_superuser", "is_active")
    fieldsets = UserAdmin.fieldsets + (
        ("Panther", {"fields": ("role", "phone", "mfa_enabled")}),
    )


from .models import TimeEntry


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ("user", "clock_in", "clock_out", "hours", "adjusted")
    list_filter = ("adjusted", "user")
    search_fields = ("user__username", "user__first_name", "user__last_name")
    date_hierarchy = "clock_in"
    list_editable = ("clock_out",)
    autocomplete_fields = ("user", "adjusted_by")


from .models import AgencySettings


@admin.register(AgencySettings)
class AgencySettingsAdmin(admin.ModelAdmin):
    list_display = ("agency_name", "currency", "late_threshold_min", "automation_enabled")
