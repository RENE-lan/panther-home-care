from django.contrib import admin
from django.urls import include, path

from accounts import views as account_views

# Branded admin site
admin.site.site_header = "Panther Home Care — Administration"
admin.site.site_title = "Panther Admin"
admin.site.index_title = "Espace d'administration"

# Add a KPI band to the admin home page.
_orig_admin_index = admin.site.index


def _panther_admin_index(request, extra_context=None):
    from django.utils import timezone
    from clients.models import Client
    from caregivers.models import Applicant, Caregiver
    from scheduling.models import Visit
    from reports.models import CareReport
    from incidents.models import Incident, IncidentStatus

    now = timezone.localtime()
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    extra_context = extra_context or {}
    extra_context["pth_stats"] = {
        "clients": Client.objects.filter(active=True).count(),
        "caregivers": Caregiver.objects.filter(active=True).count(),
        "visits_today": Visit.objects.filter(
            scheduled_start__gte=day, scheduled_start__lt=day + timezone.timedelta(days=1)).count(),
        "reports_7d": CareReport.objects.filter(
            created_at__gte=day - timezone.timedelta(days=7)).count(),
        "incidents_open": Incident.objects.exclude(status=IncidentStatus.RESOLVED).count(),
        "applicants": Applicant.objects.count(),
    }
    return _orig_admin_index(request, extra_context)


admin.site.index = _panther_admin_index

urlpatterns = [
    path("admin/", admin.site.urls),
    # Social sign-in gate (hands off to real OAuth when configured).
    path("accounts/connect/<str:provider>/", account_views.social_start, name="social_start"),
    path("accounts/", include("allauth.urls")),
    path("api/", include("scheduling.api_urls")),
    path("api/v1/", include("dashboard.api_urls")),
    path("", include("dashboard.urls")),
]
