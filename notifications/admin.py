from django.contrib import admin

from dashboard.admin_helpers import badge
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "level_badge", "recipient", "read", "created_at")
    list_filter = ("level", "read")
    search_fields = ("title", "body")
    date_hierarchy = "created_at"
    list_per_page = 30

    @admin.display(description="Niveau", ordering="level")
    def level_badge(self, obj):
        return badge(obj.get_level_display(), obj.level)
