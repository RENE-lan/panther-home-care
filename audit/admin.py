from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "target")
    search_fields = ("action", "target", "actor__username")
    date_hierarchy = "created_at"
    list_per_page = 40
    readonly_fields = ("actor", "action", "target", "created_at")

    def has_add_permission(self, request):
        return False
