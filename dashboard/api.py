"""
JSON API for the React (Vite + TypeScript) frontend.

Dependency-free (plain Django JsonResponse), session-based auth. In dev the Vite
server proxies /api to Django, so the session cookie is same-origin. For a production
SPA on a different origin you'd add proper CORS + CSRF or JWT — noted in the README.
"""
import json

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from ai.services import analytics_snapshot, daily_brief, match_caregivers
from clients.models import Client
from incidents.models import Incident, IncidentStatus
from reports.models import CareReport
from scheduling.models import Visit, VisitStatus


def _user_json(u):
    return {
        "id": u.id, "username": u.username, "email": u.email,
        "name": u.get_full_name() or u.username,
        "role": u.role, "role_label": u.get_role_display(),
    }


@csrf_exempt
@require_POST
def api_login(request):
    try:
        body = json.loads(request.body or "{}")
    except ValueError:
        body = {}
    user = authenticate(request,
                        username=body.get("username", ""),
                        password=body.get("password", ""))
    if user is None:
        return JsonResponse({"detail": "Identifiants invalides."}, status=401)
    login(request, user)
    return JsonResponse({"user": _user_json(user)})


@csrf_exempt
@require_POST
def api_logout(request):
    logout(request)
    return JsonResponse({"ok": True})


@require_GET
def api_me(request):
    if not request.user.is_authenticated:
        return JsonResponse({"user": None}, status=401)
    return JsonResponse({"user": _user_json(request.user)})


def _today():
    now = timezone.localtime()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timezone.timedelta(days=1), now


@login_required
@require_GET
def api_dashboard(request):
    start, end, now = _today()
    todays = Visit.objects.filter(scheduled_start__gte=start, scheduled_start__lt=end)
    completed = todays.filter(status=VisitStatus.COMPLETED).count()
    open_inc = Incident.objects.exclude(status=IncidentStatus.RESOLVED)

    # AI recommendation for the first uncovered visit
    recommendation = None
    uncovered = todays.filter(status=VisitStatus.UNCOVERED).select_related("client").first()
    if uncovered:
        matches = match_caregivers(uncovered, top_n=1)
        m = matches[0] if matches else None
        recommendation = {
            "visit_id": uncovered.id,
            "client": uncovered.client.code,
            "care_type": uncovered.client.care_type,
            "start": timezone.localtime(uncovered.scheduled_start).strftime("%H:%M"),
            "end": timezone.localtime(uncovered.scheduled_end).strftime("%H:%M"),
            "match": None if not m else {
                "caregiver_id": m["caregiver"].id,
                "code": m["caregiver"].code,
                "name": m["caregiver"].full_name,
                "score": m["score"],
                "distance_km": m["distance_km"],
                "components": m["components"],
                "skills_ok": m["skills_ok"],
                "workload": m["workload"],
            },
        }

    brief = daily_brief()
    late = [{
        "caregiver": v.caregiver.code if v.caregiver else "Soignant",
        "minutes_late": v.minutes_late, "client": v.client.code,
        "time": timezone.localtime(v.scheduled_start).strftime("%H:%M"),
    } for v in todays.filter(status__in=[VisitStatus.SCHEDULED, VisitStatus.IN_PROGRESS])
        .select_related("client", "caregiver") if v.minutes_late]

    flags = [{
        "client": r.visit.client.code, "concern": r.ai_concern,
        "time": timezone.localtime(r.created_at).strftime("%H:%M"),
    } for r in CareReport.objects.filter(ai_flagged=True, created_at__gte=start)
        .select_related("visit__client")[:6]]

    critical = [{
        "title": i.title, "client": i.client.code if i.client else None,
        "at": timezone.localtime(i.created_at).strftime("%d/%m %H:%M"),
    } for i in open_inc.filter(severity="CRITICAL").select_related("client")[:6]]

    return JsonResponse({
        "kpis": {
            "clients": Client.objects.filter(active=True).count(),
            "caregivers": __import__("caregivers.models", fromlist=["Caregiver"])
                .Caregiver.objects.filter(active=True).count(),
            "visits_today": todays.count(),
            "completed": completed,
            "incidents_open": open_inc.count(),
            "incidents_critical": open_inc.filter(severity="CRITICAL").count(),
        },
        "recommendation": recommendation,
        "brief": brief,
        "late": late,
        "flags": flags,
        "critical": critical,
    })


@login_required
@require_GET
def api_clients(request):
    q = request.GET.get("q", "").strip()
    qs = Client.objects.filter(active=True)
    if q:
        from django.db.models import Q
        qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q)
                       | Q(code__icontains=q))
    data = [{
        "id": c.id, "code": c.code, "name": c.full_name,
        "risk": c.risk_level, "risk_label": c.get_risk_level_display(),
        "care_type": c.care_type, "address": c.address,
        "language": c.preferred_language,
    } for c in qs.order_by("code")[:200]]
    return JsonResponse({"results": data})


@login_required
@require_GET
def api_analytics(request):
    return JsonResponse(analytics_snapshot(days=int(request.GET.get("days", 14))))
