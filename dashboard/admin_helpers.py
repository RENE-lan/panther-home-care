"""Shared admin utilities: a CSV export action and colored status badges."""
import csv

from django.http import HttpResponse
from django.utils.html import format_html

COLORS = {
    # risk / severity
    "LOW": "#1f8a4c", "MEDIUM": "#e59a1c", "HIGH": "#d93a3a", "CRITICAL": "#b01e1e",
    # incident status
    "OPEN": "#6b7688", "IN_REVIEW": "#2b6cb0", "ESCALATED": "#d93a3a", "RESOLVED": "#1f8a4c",
    # visit status
    "UNCOVERED": "#d93a3a", "SCHEDULED": "#8a97ab", "IN_PROGRESS": "#2b6cb0",
    "COMPLETED": "#1f8a4c", "MISSED": "#b01e1e", "CANCELLED": "#8a97ab",
    # alert level
    "INFO": "#2b6cb0", "ATTENTION": "#e59a1c",
}


def badge(label, key):
    color = COLORS.get(key, "#6b7688")
    return format_html('<span class="pbadge" style="background:{}">{}</span>', color, label)


def export_csv(modeladmin, request, queryset):
    meta = modeladmin.model._meta
    fields = [f.name for f in meta.fields]
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = f"attachment; filename={meta.model_name}.csv"
    writer = csv.writer(resp)
    writer.writerow(fields)
    for obj in queryset:
        writer.writerow([getattr(obj, f) for f in fields])
    return resp


export_csv.short_description = "Exporter la sélection en CSV"
