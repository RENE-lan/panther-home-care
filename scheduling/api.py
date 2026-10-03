"""
Minimal JSON API for the caregiver mobile app. Kept dependency-free (plain Django
JsonResponse) so the project runs with nothing but Django installed. Swap in DRF
later if you want serializers/browsable API.
"""
import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from ai.services import scan_report_for_risk
from reports.models import CareReport
from .models import Visit, VisitStatus


def _caregiver(request):
    return getattr(request.user, "caregiver_profile", None)


@login_required
def my_visits(request):
    """Today's visits for the logged-in caregiver — powers the mobile home screen."""
    cg = _caregiver(request)
    if not cg:
        return JsonResponse({"error": "not a caregiver"}, status=403)
    now = timezone.localtime()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    visits = cg.visits.filter(scheduled_start__gte=start,
                              scheduled_start__lt=start + timezone.timedelta(days=1))
    data = [{
        "id": v.id,
        "client": v.client.code,
        "client_name": v.client.full_name,
        "start": v.scheduled_start.isoformat(),
        "end": v.scheduled_end.isoformat(),
        "status": v.status,
    } for v in visits]
    return JsonResponse({"visits": data})


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def check_in(request, pk):
    cg = _caregiver(request)
    visit = Visit.objects.filter(pk=pk, caregiver=cg).first()
    if not visit:
        return JsonResponse({"error": "not found"}, status=404)
    body = json.loads(request.body or "{}")
    visit.check_in(lat=body.get("lat"), lng=body.get("lng"))
    return JsonResponse({"status": visit.status, "check_in_at": visit.check_in_at.isoformat()})


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def submit_report(request, pk):
    """Complete a visit and file the care report; AI scans it for concerns on save."""
    cg = _caregiver(request)
    visit = Visit.objects.filter(pk=pk, caregiver=cg).first()
    if not visit:
        return JsonResponse({"error": "not found"}, status=404)
    body = json.loads(request.body or "{}")
    report, _ = CareReport.objects.update_or_create(
        visit=visit,
        defaults={
            "caregiver": cg,
            "notes": body.get("notes", ""),
            "mood": int(body.get("mood", 3)),
            "blood_pressure": body.get("blood_pressure", ""),
            "pulse": body.get("pulse", ""),
            "tasks_completed": body.get("tasks_completed", []),
        },
    )
    if visit.status != VisitStatus.COMPLETED:
        visit.check_out()
    concern = scan_report_for_risk(report)
    return JsonResponse({"report_id": report.id, "ai_flagged": report.ai_flagged,
                         "ai_concern": concern})
