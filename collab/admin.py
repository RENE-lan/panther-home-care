from django.contrib import admin
from .models import WorkItem, WorkItemEvent, Meeting, MeetingParticipant


@admin.register(WorkItem)
class WorkItemAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "priority", "status", "due_at")
    list_filter = ("status", "category", "priority")


admin.site.register(WorkItemEvent)


class PartInline(admin.TabularInline):
    model = MeetingParticipant
    extra = 0


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ("title", "requested_by", "proposed_at", "status")
    list_filter = ("status",)
    inlines = [PartInline]
