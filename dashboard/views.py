import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from ai.services import analytics_snapshot, daily_brief, match_caregivers
from audit.models import log
from caregivers.models import Caregiver
from clients.models import Client
from dashboard import pdf as pdfgen
from incidents.models import Incident, IncidentStatus, Severity
from reports.models import CareReport
from scheduling.models import Visit, VisitStatus


def _pdf_response(data, filename, download=False):
    """Serve PDF bytes inline (viewer) or as an attachment (download)."""
    resp = HttpResponse(data, content_type="application/pdf")
    disp = "attachment" if download else "inline"
    resp["Content-Disposition"] = f'{disp}; filename="{filename}"'
    return resp


def _today_window():
    now = timezone.localtime()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timezone.timedelta(days=1)


def _mini_map_svg(clients, caregivers, uncovered):
    """Server-rendered compact operations map for the dashboard preview."""
    from django.utils.safestring import mark_safe
    pts = [(c.latitude, c.longitude) for c in clients if c.latitude] + \
          [(cg.home_latitude, cg.home_longitude) for cg in caregivers if cg.home_latitude]
    if not pts:
        return mark_safe("")
    lats = [p[0] for p in pts]; lngs = [p[1] for p in pts]
    mnla, mxla, mnlo, mxlo = min(lats), max(lats), min(lngs), max(lngs)
    dla = (mxla - mnla) or 0.01; dlo = (mxlo - mnlo) or 0.01
    mnla -= dla * .08; mxla += dla * .08; mnlo -= dlo * .08; mxlo += dlo * .08
    W, H, P = 340, 190, 12
    X = lambda lng: P + (lng - mnlo) / (mxlo - mnlo) * (W - 2 * P)
    Y = lambda lat: P + (mxla - lat) / (mxla - mnla) * (H - 2 * P)
    RISK = {"LOW": "#1f8a4c", "MEDIUM": "#e59a1c", "HIGH": "#d93a3a", "CRITICAL": "#b01e1e"}
    s = [f'<svg viewBox="0 0 {W} {H}" class="minimap-svg" xmlns="http://www.w3.org/2000/svg">']
    s.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#eef2f7"/>')
    for i in range(1, 6):
        gx = P + i * (W - 2 * P) / 6
        s.append(f'<line x1="{gx:.0f}" y1="{P}" x2="{gx:.0f}" y2="{H-P}" stroke="#dde4ee"/>')
    for cg in caregivers:
        if cg.home_latitude:
            x, y = X(cg.home_longitude), Y(cg.home_latitude)
            s.append(f'<rect x="{x-2.5:.1f}" y="{y-2.5:.1f}" width="5" height="5" rx="1" fill="#2b6cb0" opacity=".8"/>')
    for c in clients:
        if c.latitude:
            x, y = X(c.longitude), Y(c.latitude)
            col = RISK.get(c.risk_level, "#6b7688")
            s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.6" fill="{col}" stroke="#fff" stroke-width="1"/>')
    if uncovered and uncovered.client.latitude:
        x, y = X(uncovered.client.longitude), Y(uncovered.client.latitude)
        s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="#e8622a" stroke="#fff" stroke-width="2"/>')
        s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="10" fill="none" stroke="#e8622a" stroke-width="1.4" opacity=".5"/>')
    s.append('</svg>')
    return mark_safe("".join(s))


@login_required
def home(request):
    """Coordinator dashboard — an AI-powered operations cockpit."""
    if getattr(request.user, "is_family", False) or (
            getattr(request.user, "linked_clients", None) and request.user.linked_clients.exists()):
        return redirect("dashboard:family_home")
    from datetime import timedelta

    from django.db.models import Avg
    from caregivers.models import Caregiver as CG
    from reports.models import CareReport as CR

    start, end = _today_window()
    todays = list(Visit.objects.filter(scheduled_start__gte=start, scheduled_start__lt=end)
                  .exclude(status=VisitStatus.CANCELLED)
                  .select_related("client", "caregiver").order_by("scheduled_start"))

    uncovered = [v for v in todays if v.is_uncovered]
    from accounts.models import AgencySettings
    _cfg = AgencySettings.get()
    late = [v for v in todays if v.minutes_late >= _cfg.late_threshold_min]
    completed = sum(1 for v in todays if v.status == VisitStatus.COMPLETED)
    total = len(todays)
    remaining = total - completed
    confirmed = sum(1 for v in todays if not v.is_uncovered)

    # KPI trends (week over week)
    wk = start - timedelta(days=7)
    new_clients = Client.objects.filter(created_at__gte=wk).count()
    new_caregivers = CG.objects.filter(created_at__gte=wk).count()

    # Incident breakdown by severity (open only)
    open_inc = Incident.objects.exclude(status=IncidentStatus.RESOLVED)
    inc = {
        "critical": open_inc.filter(severity=Severity.CRITICAL).count(),
        "high": open_inc.filter(severity=Severity.HIGH).count(),
        "medium": open_inc.filter(severity=Severity.MEDIUM).count(),
        "low": open_inc.filter(severity=Severity.LOW).count(),
    }
    inc["total"] = sum(inc.values())

    # AI recommendation for the first uncovered shift
    top_uncovered = uncovered[0] if uncovered else None
    recommendation = None
    if top_uncovered:
        matches = match_caregivers(top_uncovered, top_n=1)
        recommendation = {"visit": top_uncovered, "match": matches[0] if matches else None}

    # Decision cards: for each uncovered visit, how many qualified caregivers are near
    from ai.services import carematch_ranked
    uncovered_actions = []
    for v in uncovered[:5]:
        ms = carematch_ranked(v, top_n=10)
        near = [m for m in ms if m["distance_km"] is not None and m["distance_km"] <= 5]
        qualified = [m for m in ms if m["score"] >= 65]
        uncovered_actions.append({
            "visit": v, "top": ms[0] if ms else None,
            "near": len(near), "qualified": len(qualified),
        })

    flagged = list(CareReport.objects.filter(ai_flagged=True, created_at__gte=start)
                   .select_related("visit__client", "caregiver")[:5])

    # Today's schedule timeline (compact bars 6:00–20:00)
    H0, H1 = 6, 20
    schedule = []
    for v in todays:
        s = timezone.localtime(v.scheduled_start)
        e = timezone.localtime(v.scheduled_end)
        sh, eh = s.hour + s.minute / 60, e.hour + e.minute / 60
        left = max(0, (sh - H0) / (H1 - H0) * 100)
        width = min(100 - left, max(4, (eh - sh) / (H1 - H0) * 100))
        schedule.append({"visit": v, "time": s.strftime("%H:%M"),
                         "left": round(left, 1), "width": round(width, 1),
                         "late": v.minutes_late, "uncovered": v.is_uncovered})

    # Weekly performance
    wk_visits = Visit.objects.filter(scheduled_start__gte=start - timedelta(days=6),
                                     scheduled_start__lt=end).exclude(status=VisitStatus.CANCELLED)
    wk_completed = wk_visits.filter(status=VisitStatus.COMPLETED)
    wk_total_n = wk_visits.count() or 1
    done_pct = round(100 * wk_completed.count() / wk_total_n)
    on_time = sum(1 for v in wk_completed.only("check_in_at", "scheduled_start")
                  if v.check_in_at and (v.check_in_at - v.scheduled_start).total_seconds() <= 600)
    punctuality = round(100 * on_time / (wk_completed.count() or 1))
    avg_mood = CR.objects.filter(created_at__gte=start - timedelta(days=6)).aggregate(m=Avg("mood"))["m"] or 0
    satisfaction = round(avg_mood * 20)
    inc_this = open_inc.filter(created_at__gte=start - timedelta(days=6)).count()
    inc_prev = Incident.objects.filter(created_at__gte=start - timedelta(days=13),
                                       created_at__lt=start - timedelta(days=6)).count()
    inc_trend = round(100 * (inc_this - inc_prev) / inc_prev) if inc_prev else 0

    # Map preview
    clients_geo = list(Client.objects.filter(active=True, latitude__isnull=False))
    cgs_geo = list(CG.objects.filter(active=True, home_latitude__isnull=False))

    # ---- Manager overviews (client, caregiver, billing, tasks) ----
    from datetime import timedelta as _td
    from django.db.models import Count as _Count
    from clients.models import Invoice, CareConcern
    from caregivers.models import Certification
    from scheduling.models import VisitRequest
    today = timezone.localdate()
    month_start = start.replace(day=1)

    client_overview = {
        "active": Client.objects.filter(active=True).count(),
        "new_month": Client.objects.filter(created_at__gte=month_start).count(),
        "high_risk": Client.objects.filter(active=True, risk_level__in=["HIGH", "CRITICAL"]).count(),
        "concerns": CareConcern.objects.exclude(status="RESOLVED").count(),
    }
    active_cg_ids = set(CG.objects.filter(active=True).values_list("id", flat=True))
    on_visit_ids = set(Visit.objects.filter(status=VisitStatus.IN_PROGRESS)
                       .values_list("caregiver_id", flat=True)) & active_cg_ids
    cg_overview = {
        "total": len(active_cg_ids),
        "on_visit": len(on_visit_ids),
        "available": len(active_cg_ids) - len(on_visit_ids),
        "top": list(Visit.objects.filter(scheduled_start__gte=start, scheduled_start__lt=end,
                                         caregiver__isnull=False)
                    .values("caregiver__code").annotate(n=_Count("id")).order_by("-n")[:4]),
    }
    certs_expiring = Certification.objects.filter(expires_on__gte=today,
                                                  expires_on__lte=today + _td(days=60)).count()
    certs_expired = Certification.objects.filter(expires_on__lt=today).count()

    all_inv = Invoice.objects.all()
    billing = {
        "billed": sum(i.amount for i in all_inv),
        "revenue_month": sum(i.amount for i in all_inv if i.issued_date >= month_start.date()),
        "paid": sum(i.amount for i in all_inv if i.status == "PAID"),
        "outstanding": sum(i.amount for i in all_inv if i.status != "PAID"),
        "overdue": sum(i.amount for i in all_inv
                       if i.status != "PAID" and (i.due_date or i.issued_date) < today),
    }
    tasks = {
        "requests": VisitRequest.objects.filter(status="PENDING").count(),
        "certs": certs_expiring + certs_expired,
        "critical": inc["critical"],
        "uncovered": len(uncovered),
        "concerns": client_overview["concerns"],
    }
    tasks["total"] = tasks["requests"] + tasks["certs"] + tasks["critical"] + tasks["uncovered"]

    # ---- Panther Command Center: "what needs my attention right now?" ----
    recent_completed = Visit.objects.filter(status=VisitStatus.COMPLETED,
                                            scheduled_start__gte=start - _td(days=14))
    documented_ids = set(CareReport.objects.filter(
        visit__in=recent_completed).values_list("visit_id", flat=True))
    unsigned = recent_completed.exclude(id__in=documented_ids).count()
    to_approve = Visit.objects.filter(status=VisitStatus.COMPLETED, hours_approved=False,
                                      scheduled_start__gte=start - _td(days=30)).count()
    billing_ready = Visit.objects.filter(status=VisitStatus.COMPLETED,
                                         hours_approved=True).count()
    command = [
        {"n": len(uncovered), "label": "visites non couvertes", "tone": "r",
         "url": "dashboard:copilot"},
        {"n": len(late), "label": "soignants en retard", "tone": "a",
         "url": "dashboard:live"},
        {"n": unsigned, "label": "rapports de visite à compléter", "tone": "a",
         "url": "dashboard:reports"},
        {"n": to_approve, "label": "heures à approuver", "tone": "a",
         "url": "dashboard:hours_approval"},
        {"n": certs_expiring + certs_expired, "label": "certifications à renouveler", "tone": "y",
         "url": "dashboard:compliance"},
        {"n": billing_ready, "label": "visites prêtes à facturer", "tone": "m",
         "url": "dashboard:billing"},
    ]
    command_total = sum(c["n"] for c in command)

    from ai.services import coordinator_actions
    ai_actions = coordinator_actions(6)

    # 14-day visits trend (for the dashboard chart)
    trend = {"labels": [], "done": [], "planned": []}
    for i in range(13, -1, -1):
        d0 = start - _td(days=i)
        d1 = d0 + _td(days=1)
        dv = Visit.objects.filter(scheduled_start__gte=d0, scheduled_start__lt=d1)
        trend["labels"].append(d0.strftime("%d/%m"))
        trend["done"].append(dv.filter(status=VisitStatus.COMPLETED).count())
        trend["planned"].append(dv.exclude(status=VisitStatus.CANCELLED).count())

    context = {
        "kpi_clients": Client.objects.filter(active=True).count(),
        "kpi_caregivers": CG.objects.filter(active=True).count(),
        "kpi_visits_today": total,
        "new_clients": new_clients, "new_caregivers": new_caregivers,
        "kpi_incidents_open": inc["total"],
        "kpi_incidents_critical": inc["critical"],
        "incidents": inc,
        "client_overview": client_overview,
        "cg_overview": cg_overview,
        "billing": billing,
        "tasks": tasks,
        "command": command,
        "command_total": command_total,
        "ai_actions": ai_actions,
        "trend": trend,
        "certs_expiring": certs_expiring,
        "brief": daily_brief(),
        "recommendation": recommendation,
        "uncovered_actions": uncovered_actions,
        "uncovered": uncovered,
        "late": late,
        "completed": completed, "remaining": remaining, "confirmed": confirmed,
        "total": total,
        "schedule": schedule,
        "performance": {"done": done_pct, "punctuality": punctuality,
                        "satisfaction": satisfaction, "inc_trend": inc_trend},
        "map_svg": _mini_map_svg(clients_geo, cgs_geo, top_uncovered),
        "map_counts": {"ok": confirmed - len(late), "late": len(late), "problem": len(uncovered)},
        "critical_incidents": open_inc.filter(severity=Severity.CRITICAL)
            .select_related("client")[:5],
        "flagged_reports": flagged,
        "attention_reports": flagged,
    }
    return render(request, "dashboard/home.html", context)


@login_required
def visit_detail(request, pk):
    from ai.services import client_continuity, carematch_ranked
    visit = get_object_or_404(Visit.objects.select_related("client", "caregiver"), pk=pk)
    matches = carematch_ranked(visit, top_n=6) if visit.is_uncovered else []
    continuity = client_continuity(visit.client)
    max_visits = max((c["visits"] for c in continuity), default=1) or 1
    for c in continuity:
        c["pct"] = round(100 * c["visits"] / max_visits)
    continuity_risk = continuity[0] if continuity and continuity[0]["visits"] >= 4 else None
    return render(request, "dashboard/visit_detail.html", {
        "visit": visit, "matches": matches,
        "recommended": matches[0] if matches else None,
        "alternatives": matches[1:3] if len(matches) > 1 else [],
        "others": matches[3:] if len(matches) > 3 else [],
        "continuity": continuity, "continuity_risk": continuity_risk,
    })


@login_required
@require_POST
def approve_assignment(request, pk):
    """Approve the AI-recommended caregiver (or a chosen one) for an uncovered visit."""
    visit = get_object_or_404(Visit, pk=pk)
    caregiver_id = request.POST.get("caregiver_id")
    if caregiver_id:
        caregiver = get_object_or_404(Caregiver, pk=caregiver_id)
    else:
        matches = match_caregivers(visit, top_n=1)
        caregiver = matches[0]["caregiver"] if matches else None

    if caregiver:
        visit.caregiver = caregiver
        visit.status = VisitStatus.SCHEDULED
        visit.save(update_fields=["caregiver", "status"])
        log(request.user, "A approuvé une affectation",
            f"{visit.client.code} → {caregiver.code}")
    return redirect("dashboard:home")


@login_required
def clients_list(request):
    q = request.GET.get("q", "").strip()
    clients = Client.objects.all().prefetch_related("invoices")
    if q:
        clients = clients.filter(Q(code__icontains=q) | Q(first_name__icontains=q) |
                                 Q(last_name__icontains=q))
    rows = []
    for c in clients:
        invs = list(c.invoices.all())
        if not invs:
            pay = "none"
        elif any(i.status != "PAID" for i in invs):
            pay = "unpaid"
        else:
            pay = "paid"
        rows.append({"c": c, "pay": pay})
    return render(request, "dashboard/clients.html", {"rows": rows, "q": q})


@login_required
def client_360(request, pk):
    """Client 360° — everything about one client on a single screen."""
    from clients.models import ClientContract
    client = get_object_or_404(Client, pk=pk)
    if request.method == "POST" and _office_only(request):
        from datetime import datetime
        try:
            sd = datetime.strptime(request.POST.get("start_date"), "%Y-%m-%d").date()
        except (ValueError, TypeError):
            sd = timezone.localdate()
        ClientContract.objects.create(
            client=client, reference=request.POST.get("reference", "").strip(),
            hours_per_week=request.POST.get("hours_per_week") or 10,
            hourly_rate=request.POST.get("hourly_rate") or client.bill_rate,
            start_date=sd, status=request.POST.get("status", "ACTIVE"),
            notes=request.POST.get("notes", "").strip())
        log(request.user, "A créé un contrat", client.code)
        messages.success(request, "Contrat enregistré.")
        return redirect("dashboard:client_360", pk=pk)
    visits = client.visits.select_related("caregiver").order_by("-scheduled_start")
    timeline = _build_timeline(client)
    return render(request, "dashboard/client_360.html", {
        "client": client,
        "upcoming": visits.filter(scheduled_start__gte=timezone.now())[:5],
        "past": visits.filter(scheduled_start__lt=timezone.now())[:8],
        "incidents": client.incidents.all()[:8],
        "timeline": timeline,
        "contracts": client.contracts.all(),
        "assessments": client.assessments.all(),
        "invoices": client.invoices.all(),
        "today": timezone.localdate().isoformat(),
    })


def _build_timeline(client):
    """Interleave visits, reports and incidents into one care-intelligence timeline."""
    events = []
    for v in client.visits.select_related("caregiver")[:20]:
        events.append((v.scheduled_start, "visit", v))
        if v.check_in_at:
            events.append((v.check_in_at, "checkin", v))
    for r in CareReport.objects.filter(visit__client=client)[:20]:
        events.append((r.created_at, "report", r))
        if r.ai_flagged:
            events.append((r.created_at, "ai_flag", r))
    for i in client.incidents.all()[:20]:
        events.append((i.created_at, "incident", i))
    events.sort(key=lambda e: e[0], reverse=True)
    return events[:25]


@login_required
def caregivers_list(request):
    return render(request, "dashboard/caregivers.html",
                  {"caregivers": Caregiver.objects.prefetch_related("skills").order_by("code")})


@login_required
def caregiver_360(request, pk):
    from datetime import timedelta
    from django.db.models import Count
    from caregivers.models import CaregiverEvaluation, CaregiverDocument, Availability
    from notifications.models import Notification, AlertLevel
    caregiver = get_object_or_404(Caregiver, pk=pk)
    now = timezone.localtime()

    if request.method == "POST" and _office_only(request):
        action = request.POST.get("action", "evaluate")
        if action == "document":
            CaregiverDocument.objects.create(
                caregiver=caregiver, name=request.POST.get("name", "").strip() or "Document",
                doc_type=request.POST.get("doc_type", "OTHER"),
                status=request.POST.get("status", "VALID"),
                reference=request.POST.get("reference", "").strip(),
                expires_on=request.POST.get("expires_on") or None)
            messages.success(request, "Document ajouté.")
        elif action == "message":
            body = request.POST.get("body", "").strip()
            if body and caregiver.user_id:
                from notifications.services import notify
                notify(caregiver.user, request.POST.get("subject", "Message de l'agence").strip()
                       or "Message de l'agence", body, email=True)
                messages.success(request, "Message envoyé au soignant.")
            elif not caregiver.user_id:
                messages.info(request, "Ce soignant n'a pas de compte lié.")
        else:
            CaregiverEvaluation.objects.create(
                caregiver=caregiver, period=request.POST.get("period", "").strip() or "—",
                punctuality=int(request.POST.get("punctuality") or 4),
                care_quality=int(request.POST.get("care_quality") or 4),
                communication=int(request.POST.get("communication") or 4),
                professionalism=int(request.POST.get("professionalism") or 4),
                notes=request.POST.get("notes", "").strip(), evaluator=request.user)
            log(request.user, "A évalué un soignant", caregiver.code)
            messages.success(request, "Évaluation enregistrée.")
        return redirect("dashboard:caregiver_360", pk=pk)

    evaluations = list(caregiver.evaluations.select_related("evaluator"))
    avg_eval = round(sum(e.score for e in evaluations) / len(evaluations)) if evaluations else None

    wd = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
    availability = [{"day": wd[a.weekday] if a.weekday < 7 else "?",
                     "start": a.start_time, "end": a.end_time}
                    for a in Availability.objects.filter(caregiver=caregiver)]

    clients_served = (caregiver.visits.filter(status=VisitStatus.COMPLETED, client__isnull=False)
                      .values("client__code", "client__first_name")
                      .annotate(n=Count("id")).order_by("-n")[:20])

    evv_rows = []
    for v in (caregiver.visits.filter(check_in_at__isnull=False)
              .select_related("client").order_by("-check_in_at")[:15]):
        e = _evv_state(v) or {}
        evv_rows.append({"visit": v, **e})

    # Timesheets: last 4 weeks of hours
    ts = []
    for w in range(4):
        wk_start = (now - timedelta(days=now.weekday() + 7 * w)).replace(hour=0, minute=0, second=0, microsecond=0)
        wk_end = wk_start + timedelta(days=7)
        hrs = sum((v.check_out_at - v.check_in_at).total_seconds() / 3600
                  for v in caregiver.visits.filter(status=VisitStatus.COMPLETED,
                                                    scheduled_start__gte=wk_start, scheduled_start__lt=wk_end)
                  if v.check_in_at and v.check_out_at)
        ts.append({"label": wk_start.strftime("Sem. %d/%m"), "hours": round(hrs, 1)})

    return render(request, "dashboard/caregiver_360.html", {
        "caregiver": caregiver, "evaluations": evaluations, "avg_eval": avg_eval,
        "upcoming": caregiver.visits.filter(scheduled_start__gte=now)
                    .select_related("client").order_by("scheduled_start")[:10],
        "recent": caregiver.visits.filter(scheduled_start__lt=now, status=VisitStatus.COMPLETED)
                  .select_related("client").order_by("-scheduled_start")[:10],
        "certifications": caregiver.certifications.all(),
        "availability": availability, "clients_served": clients_served,
        "documents": caregiver.documents.all(), "evv_rows": evv_rows, "timesheets": ts,
        "incidents": caregiver.incidents.select_related("client").all()[:15],
        "cg_messages": (Notification.objects.filter(recipient=caregiver.user)[:20]
                        if caregiver.user_id else []),
        "today": timezone.localdate().isoformat(),
    })


@login_required
def schedule(request):
    """Day-timeline grid: caregivers as rows, hours as columns, visits as blocks."""
    day_offset = int(request.GET.get("d", 0))
    base = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    day = base + timezone.timedelta(days=day_offset)
    nxt = day + timezone.timedelta(days=1)

    HOUR_START, HOUR_END = 6, 20  # visible window
    span = HOUR_END - HOUR_START
    hours = list(range(HOUR_START, HOUR_END))  # left-edge labels (6..19), 14 columns

    visits = (Visit.objects.filter(scheduled_start__gte=day, scheduled_start__lt=nxt)
              .exclude(status=VisitStatus.CANCELLED)
              .select_related("client", "caregiver").order_by("scheduled_start"))

    rows = {}          # caregiver -> list of blocks
    unassigned = []
    for v in visits:
        s = timezone.localtime(v.scheduled_start)
        e = timezone.localtime(v.scheduled_end)
        start_h = s.hour + s.minute / 60
        end_h = e.hour + e.minute / 60
        left = max(0, (start_h - HOUR_START) / span * 100)
        width = min(100 - left, (end_h - start_h) / span * 100)
        block = {
            "visit": v, "left": round(left, 2), "width": round(max(width, 4), 2),
            "label": f"{s:%H:%M} {v.client.code}",
            "status": v.status, "uncovered": v.is_uncovered,
        }
        if v.caregiver:
            rows.setdefault(v.caregiver, []).append(block)
        else:
            unassigned.append(block)

    grid = [{"caregiver": cg, "blocks": bl} for cg, bl in
            sorted(rows.items(), key=lambda kv: kv[0].code)]
    return render(request, "dashboard/schedule.html", {
        "grid": grid, "unassigned": unassigned, "hours": hours,
        "day": day, "day_offset": day_offset,
        "prev_offset": day_offset - 1, "next_offset": day_offset + 1,
    })


@login_required
def analytics(request):
    days = int(request.GET.get("days", 14))
    data = analytics_snapshot(days=days)
    bi = _management_intelligence()
    from ai.services import churn_ranked, demand_forecast
    return render(request, "dashboard/analytics.html",
                  {"a": data, "data_json": data, "bi": bi,
                   "churn": churn_ranked(8), "forecast": demand_forecast(7),
                                                        "days": days})


@login_required
def operations_map(request):
    """Geospatial operations view — clients and caregivers plotted on a schematic map."""
    clients = [{
        "code": c.code, "name": c.full_name, "lat": c.latitude, "lng": c.longitude,
        "risk": c.risk_level, "care": c.care_type or "",
        "type": "client",
    } for c in Client.objects.filter(active=True, latitude__isnull=False)]

    caregivers = [{
        "code": cg.code, "name": cg.full_name, "lat": cg.home_latitude, "lng": cg.home_longitude,
        "type": "caregiver",
    } for cg in Caregiver.objects.filter(active=True, home_latitude__isnull=False)]

    # If there's an uncovered visit, draw the AI match lines from client to candidates.
    match_lines = []
    focus = None
    uncovered = next((v for v in Visit.objects.filter(status=VisitStatus.UNCOVERED)
                      .select_related("client")), None)
    if uncovered and uncovered.client.latitude:
        focus = {"code": uncovered.client.code, "lat": uncovered.client.latitude,
                 "lng": uncovered.client.longitude}
        for m in match_caregivers(uncovered, top_n=3):
            cg = m["caregiver"]
            if cg.home_latitude:
                match_lines.append({
                    "code": cg.code, "lat": cg.home_latitude, "lng": cg.home_longitude,
                    "score": m["score"], "km": m["distance_km"],
                })

    payload = {"clients": clients, "caregivers": caregivers,
               "focus": focus, "match_lines": match_lines}
    return render(request, "dashboard/map.html", {"data_json": payload,
                                                  "n_clients": len(clients),
                                                  "n_caregivers": len(caregivers)})


@login_required
def recruitment(request):
    """Talent Hub — recruitment + training pipeline (in-app, not the admin)."""
    from caregivers.models import Applicant, ApplicationStage
    stages = []
    for key, label in ApplicationStage.choices:
        apps = list(Applicant.objects.filter(stage=key).order_by("-created_at"))
        stages.append({"key": key, "label": label, "applicants": apps, "count": len(apps)})
    return render(request, "dashboard/recruitment.html", {
        "stages": stages,
        "total": Applicant.objects.count(),
        "active": Applicant.objects.filter(stage=ApplicationStage.ACTIVE).count(),
        "training": Applicant.objects.filter(stage=ApplicationStage.TRAINING).count(),
    })


@login_required
def settings_page(request):
    """Central configuration — these settings actually drive EVV, automations, billing…"""
    from accounts.models import AgencySettings, User
    from audit.models import AuditLog
    s = AgencySettings.get()

    if request.method == "POST" and _office_only(request):
        section = request.POST.get("section", "")

        def b(k):
            return request.POST.get(k) == "on"

        def i(k, d):
            try:
                return int(request.POST.get(k, d))
            except (ValueError, TypeError):
                return d

        def dec(k, d):
            from decimal import Decimal, InvalidOperation
            try:
                return Decimal(str(request.POST.get(k, d)).replace(",", "."))
            except (InvalidOperation, ValueError, TypeError):
                return d

        if section == "agency":
            s.agency_name = request.POST.get("agency_name", s.agency_name).strip() or s.agency_name
            s.address = request.POST.get("address", s.address).strip()
            s.contact_email = request.POST.get("contact_email", s.contact_email).strip()
            s.contact_phone = request.POST.get("contact_phone", s.contact_phone).strip()
            s.currency = (request.POST.get("currency", s.currency).strip() or "$")[:6]
            s.business_hours = request.POST.get("business_hours", s.business_hours).strip()
            s.default_visit_minutes = i("default_visit_minutes", s.default_visit_minutes)
        elif section == "evv":
            s.late_threshold_min = i("late_threshold_min", s.late_threshold_min)
            s.geofence_km = dec("geofence_km", s.geofence_km)
            s.require_gps = b("require_gps")
        elif section == "scheduling":
            s.max_weekly_hours = i("max_weekly_hours", s.max_weekly_hours)
            s.max_travel_km = i("max_travel_km", s.max_travel_km)
            s.auto_replacement = b("auto_replacement")
        elif section == "billing":
            s.default_bill_rate = dec("default_bill_rate", s.default_bill_rate)
            s.default_pay_rate = dec("default_pay_rate", s.default_pay_rate)
            s.payment_terms_days = i("payment_terms_days", s.payment_terms_days)
            s.tax_rate = dec("tax_rate", s.tax_rate)
            s.invoice_prefix = request.POST.get("invoice_prefix", s.invoice_prefix).strip()[:10]
        elif section == "ai":
            s.automation_enabled = b("automation_enabled")
            s.ai_auto_fill = b("ai_auto_fill")
            s.ai_confidence_threshold = i("ai_confidence_threshold", s.ai_confidence_threshold)
        elif section == "notifications":
            for f in ["notify_email", "notify_sms", "alert_late", "alert_missed",
                      "alert_incident", "alert_cert", "alert_billing"]:
                setattr(s, f, b(f))
        s.save()
        log(request.user, "A modifié les paramètres", section)
        messages.success(request, "Paramètres enregistrés — appliqués à tout le système.")
        return redirect("dashboard:settings")

    return render(request, "dashboard/settings.html", {
        "s": s,
        "users": User.objects.order_by("role", "username")[:50],
        "audit": AuditLog.objects.select_related("actor").all()[:20],
        "email_ok": bool(getattr(settings, "EMAIL_HOST", "")),
        "sms_ok": bool(getattr(settings, "TWILIO_ACCOUNT_SID", "")),
        "ai_ok": bool(getattr(settings, "AI_API_KEY", "")),
    })


@login_required
def notifications_list(request):
    from django.db.models import Q
    from notifications.models import Notification
    qs = Notification.objects.filter(Q(recipient=request.user) | Q(recipient__isnull=True))
    if request.method == "POST":
        qs.filter(read=False).update(read=True, acknowledged_at=timezone.now())
        return redirect("dashboard:notifications")
    return render(request, "dashboard/notifications.html", {
        "notifications": qs[:100],
        "unread": qs.filter(read=False).count(),
    })


@login_required
def incidents_list(request):
    return render(request, "dashboard/incidents.html",
                  {"incidents": Incident.objects.select_related("client", "caregiver")})


@login_required
def reports_list(request):
    reports = CareReport.objects.select_related(
        "visit__client", "caregiver").order_by("-created_at")
    flagged_only = request.GET.get("flagged") == "1"
    if flagged_only:
        reports = reports.filter(ai_flagged=True)
    return render(request, "dashboard/reports.html", {
        "reports": reports[:100],
        "flagged_only": flagged_only,
        "flagged_count": CareReport.objects.filter(ai_flagged=True).count(),
    })


@login_required
def report_detail(request, pk):
    report = get_object_or_404(
        CareReport.objects.select_related("visit__client", "caregiver"), pk=pk)
    return render(request, "dashboard/report_detail.html", {"report": report})


# --- PDF export --------------------------------------------------------------
@login_required
def client_pdf(request, pk):
    client = get_object_or_404(Client, pk=pk)
    data = pdfgen.client_dossier_pdf(client)
    log(request.user, "A exporte un dossier PDF", client.code)
    return _pdf_response(data, f"dossier-{slugify(client.code)}.pdf",
                         download="download" in request.GET)


@login_required
def report_pdf(request, pk):
    report = get_object_or_404(CareReport.objects.select_related("visit__client"), pk=pk)
    fam = _family_client(request)
    if fam is not None and report.visit.client_id != fam.id:
        messages.info(request, "Accès non autorisé.")
        return redirect("dashboard:family_home")
    data = pdfgen.care_report_pdf(report)
    return _pdf_response(data, f"rapport-{slugify(report.visit.client.code)}-{report.id}.pdf",
                         download="download" in request.GET)


@login_required
def brief_pdf(request):
    data = pdfgen.daily_brief_pdf()
    stamp = timezone.localtime().strftime("%Y%m%d")
    return _pdf_response(data, f"brief-{stamp}.pdf", download="download" in request.GET)


# ---- Caregiver self-service: open visits & requests --------------------------------
def _caregiver(request):
    return getattr(request.user, "caregiver_profile", None)


@login_required
def open_visits(request):
    """Caregiver-facing marketplace of unfilled visits for the next 45 days."""
    from ai.services import open_visits_for
    cg = _caregiver(request)
    if cg is None:
        messages.info(request, "Les visites ouvertes sont réservées aux soignants.")
        return redirect("dashboard:home")

    rows = open_visits_for(cg, days=45)

    # Filters
    max_km = request.GET.get("max_km", "").strip()
    care = request.GET.get("care", "").strip()
    sort = request.GET.get("sort", "score")
    if max_km:
        try:
            lim = float(max_km)
            rows = [r for r in rows if r["distance_km"] is not None and r["distance_km"] <= lim]
        except ValueError:
            pass
    if care:
        rows = [r for r in rows if r["visit"].client.care_type == care]
    if sort == "date":
        rows.sort(key=lambda r: r["visit"].scheduled_start)
    elif sort == "distance":
        rows.sort(key=lambda r: (r["distance_km"] is None, r["distance_km"] or 0))
    else:
        rows.sort(key=lambda r: r["score"], reverse=True)

    my_pending = set(cg.visit_requests.filter(status="PENDING").values_list("visit_id", flat=True))
    care_types = sorted({r["visit"].client.care_type for r in open_visits_for(cg, 45)
                         if r["visit"].client.care_type})
    return render(request, "dashboard/open_visits.html", {
        "rows": rows, "care_types": care_types, "my_pending": my_pending,
        "f_max_km": max_km, "f_care": care, "f_sort": sort,
    })


@login_required
@require_POST
def request_visit(request, pk):
    from ai.services import caregiver_visit_score
    from scheduling.models import VisitRequest
    cg = _caregiver(request)
    if cg is None:
        return redirect("dashboard:home")
    visit = get_object_or_404(Visit, pk=pk, status=VisitStatus.UNCOVERED)
    score = caregiver_visit_score(cg, visit)["score"]
    obj, created = VisitRequest.objects.get_or_create(
        visit=visit, caregiver=cg, defaults={"score": score})
    if created:
        log(request.user, "A demandé une visite ouverte", visit.client.code)
        messages.success(request, "Demande envoyée. En attente de validation par le bureau.")
    else:
        messages.info(request, "Vous avez déjà demandé cette visite.")
    return redirect("dashboard:my_requests")


@login_required
def my_requests(request):
    cg = _caregiver(request)
    if cg is None:
        messages.info(request, "Réservé aux soignants.")
        return redirect("dashboard:home")
    reqs = cg.visit_requests.select_related("visit__client").all()
    return render(request, "dashboard/my_requests.html", {"requests": reqs})


@login_required
def visit_requests(request):
    """Coordinator approval queue for caregiver visit requests."""
    from scheduling.models import VisitRequest
    if not (request.user.is_staff or getattr(request.user, "is_coordinator", False)):
        messages.info(request, "Réservé au bureau.")
        return redirect("dashboard:home")
    pending = (VisitRequest.objects.filter(status="PENDING")
               .select_related("visit__client", "caregiver").order_by("visit_id", "-score"))
    recent = (VisitRequest.objects.exclude(status="PENDING")
              .select_related("visit__client", "caregiver")[:15])
    # Care Risk Radar
    now = timezone.localtime()
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    todays = Visit.objects.filter(scheduled_start__gte=day, scheduled_start__lt=day + timezone.timedelta(days=1))
    radar = {
        "pending": pending.count(),
        "high_risk": pending.filter(score__lt=65).count(),
        "uncovered": Visit.objects.filter(status=VisitStatus.UNCOVERED,
                                           scheduled_start__gte=now).count(),
        "late_risk": sum(1 for v in todays.filter(status=VisitStatus.SCHEDULED)
                         .select_related("client", "caregiver") if v.minutes_late > 0),
    }
    return render(request, "dashboard/visit_requests.html",
                  {"pending": pending, "recent": recent, "radar": radar})


@login_required
@require_POST
def decide_request(request, pk, decision):
    from scheduling.models import VisitRequest, RequestStatus
    from notifications.models import Notification
    if not (request.user.is_staff or getattr(request.user, "is_coordinator", False)):
        return redirect("dashboard:home")
    req = get_object_or_404(VisitRequest.objects.select_related("visit", "caregiver"), pk=pk)
    if decision == "approve":
        visit = req.visit
        visit.caregiver = req.caregiver
        visit.status = VisitStatus.SCHEDULED
        visit.save(update_fields=["caregiver", "status"])
        req.status = RequestStatus.APPROVED
        req.decided_at = timezone.now(); req.save()
        # Auto-decline the other pending requests for the same visit.
        visit.requests.filter(status=RequestStatus.PENDING).exclude(pk=req.pk).update(
            status=RequestStatus.DENIED, decided_at=timezone.now())
        log(request.user, "A approuvé une demande de visite", req.caregiver.code)
        if req.caregiver.user_id:
            Notification.objects.create(
                recipient=req.caregiver.user, level="INFO",
                title="Demande approuvée",
                body=f"Votre visite {visit.client.first_name} du "
                     f"{timezone.localtime(visit.scheduled_start):%d/%m %H:%M} est confirmée.")
        messages.success(request, f"Demande approuvée — {req.caregiver.code} affecté.")
    else:
        req.status = RequestStatus.DENIED
        req.decided_at = timezone.now(); req.save()
        messages.info(request, "Demande refusée.")
    return redirect("dashboard:visit_requests")


# ---- EVV: caregiver visit verification (clock in/out + documentation) ---------------
def _evv_state(visit):
    """Compute EVV verification for a visit that has a check-in."""
    from ai.services import haversine_km
    if not visit.check_in_at:
        return None
    late = max(0, int((visit.check_in_at - visit.scheduled_start).total_seconds() // 60))
    dist = haversine_km(visit.client.latitude, visit.client.longitude,
                        visit.check_in_lat, visit.check_in_lng)
    has_gps = visit.check_in_lat is not None
    return {"late": late, "distance": dist, "has_gps": has_gps,
            "gps_ok": has_gps and dist is not None and dist <= 1.0}


@login_required
def my_visits(request):
    """Caregiver EVV home: today + upcoming assigned visits, with clock in/out."""
    cg = _caregiver(request)
    if cg is None:
        messages.info(request, "Réservé aux soignants.")
        return redirect("dashboard:home")
    now = timezone.localtime()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    horizon = start + timezone.timedelta(days=7)
    visits = (Visit.objects.filter(caregiver=cg, scheduled_start__gte=start,
                                   scheduled_start__lt=horizon)
              .exclude(status=VisitStatus.CANCELLED)
              .select_related("client").order_by("scheduled_start"))
    rows = [{"visit": v, "evv": _evv_state(v),
             "today": timezone.localtime(v.scheduled_start).date() == now.date()}
            for v in visits]
    return render(request, "dashboard/my_visits.html", {"rows": rows, "today": now.date()})


@login_required
@require_POST
def evv_checkin(request, pk):
    cg = _caregiver(request)
    if cg is None:
        return redirect("dashboard:home")
    visit = get_object_or_404(Visit, pk=pk, caregiver=cg)

    def _f(name):
        try:
            return float(request.POST.get(name))
        except (TypeError, ValueError):
            return None

    visit.check_in(_f("lat"), _f("lng"))  # sets timestamp, GPS, status IN_PROGRESS
    log(request.user, "Pointage d'arrivée (EVV)", visit.client.code)
    messages.success(request, "Arrivée pointée. Bonne visite !")
    return redirect("dashboard:my_visits")


@login_required
def evv_document(request, pk):
    """Clock out + document the visit (tasks, vitals, notes). Runs the AI risk scan."""
    from reports.models import CareReport, Mood
    from ai.services import scan_report_for_risk
    cg = _caregiver(request)
    if cg is None:
        return redirect("dashboard:home")
    visit = get_object_or_404(Visit, pk=pk, caregiver=cg)
    plan_tasks = []
    if hasattr(visit.client, "care_plan"):
        plan_tasks = list(visit.client.care_plan.tasks.values_list("label", flat=True))
    if not plan_tasks:
        plan_tasks = ["Hygiène personnelle", "Médication", "Repas", "Mobilité"]

    if request.method == "POST":
        report, _ = CareReport.objects.get_or_create(visit=visit, defaults={"caregiver": cg})
        report.caregiver = cg
        try:
            report.mood = int(request.POST.get("mood", 3))
        except ValueError:
            report.mood = 3
        report.blood_pressure = request.POST.get("blood_pressure", "").strip()
        report.pulse = request.POST.get("pulse", "").strip()
        report.notes = request.POST.get("notes", "").strip()
        report.tasks_completed = request.POST.getlist("tasks")
        sig = request.POST.get("signature", "").strip()
        signer = request.POST.get("signed_by", "").strip()
        if sig and signer:
            report.signature = sig
            report.signed_by = signer
            report.signed_at = timezone.now()
        report.save()
        scan_report_for_risk(report)
        visit.check_out()  # sets check_out_at + status COMPLETED
        log(request.user, "Fin de visite documentée (EVV)", visit.client.code)
        messages.success(request, "Visite terminée et documentée. Merci !")
        return redirect("dashboard:my_visits")

    return render(request, "dashboard/evv_document.html",
                  {"visit": visit, "plan_tasks": plan_tasks, "moods": Mood.choices})


@login_required
def evv_exceptions(request):
    """Coordinator EVV monitor: recent check-ins with verification + exceptions."""
    if not (request.user.is_staff or getattr(request.user, "is_coordinator", False)):
        messages.info(request, "Réservé au bureau.")
        return redirect("dashboard:home")
    now = timezone.localtime()
    recent = (Visit.objects.filter(check_in_at__isnull=False)
              .select_related("client", "caregiver").order_by("-check_in_at")[:40])
    rows = []
    for v in recent:
        e = _evv_state(v)
        e["visit"] = v
        e["exception"] = e["late"] > 15 or (e["has_gps"] and not e["gps_ok"])
        rows.append(e)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    missed = (Visit.objects.filter(status=VisitStatus.SCHEDULED, scheduled_end__lt=now,
                                   scheduled_start__gte=day_start - timezone.timedelta(days=1),
                                   check_in_at__isnull=True)
              .select_related("client", "caregiver")[:20])
    return render(request, "dashboard/evv_exceptions.html",
                  {"rows": rows, "missed": missed,
                   "exceptions": sum(1 for r in rows if r["exception"])})


# ---- Timesheets & recurring schedules (scheduler tools) ----------------------------
def _office_only(request):
    return getattr(request.user, "is_office", False) or request.user.is_staff


@login_required
def timesheets(request):
    """Team timesheets: caregiver hours (from EVV data) for a selected week."""
    if not _office_only(request):
        messages.info(request, "Réservé au bureau.")
        return redirect("dashboard:home")
    now = timezone.localtime()
    try:
        offset = int(request.GET.get("w", 0))
    except ValueError:
        offset = 0
    monday = (now - timezone.timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0) + timezone.timedelta(weeks=offset)
    sunday = monday + timezone.timedelta(days=7)

    visits = (Visit.objects.filter(status=VisitStatus.COMPLETED,
                                   scheduled_start__gte=monday, scheduled_start__lt=sunday)
              .select_related("caregiver"))
    agg = {}
    for v in visits:
        cg = v.caregiver
        if not cg:
            continue
        if v.check_in_at and v.check_out_at:
            hrs = (v.check_out_at - v.check_in_at).total_seconds() / 3600
        else:
            hrs = (v.scheduled_end - v.scheduled_start).total_seconds() / 3600
        d = agg.setdefault(cg.id, {"cg": cg, "hours": 0.0, "visits": 0, "ontime": 0})
        d["hours"] += hrs
        d["visits"] += 1
        late = ((v.check_in_at - v.scheduled_start).total_seconds() / 60) if v.check_in_at else 0
        if late <= 10:
            d["ontime"] += 1
    rows = []
    for d in agg.values():
        d["hours"] = round(d["hours"], 1)
        d["ontime_pct"] = round(100 * d["ontime"] / d["visits"]) if d["visits"] else 0
        rows.append(d)
    rows.sort(key=lambda x: x["hours"], reverse=True)
    totals = {"hours": round(sum(r["hours"] for r in rows), 1),
              "visits": sum(r["visits"] for r in rows), "caregivers": len(rows)}
    return render(request, "dashboard/timesheets.html", {
        "rows": rows, "totals": totals, "week_start": monday,
        "week_end": sunday - timezone.timedelta(days=1),
        "w": offset, "prev": offset - 1, "next": offset + 1,
    })


@login_required
def recurring(request):
    """Create and list 'master week' recurring schedules."""
    from scheduling.models import RecurringSchedule
    if not _office_only(request):
        messages.info(request, "Réservé au bureau.")
        return redirect("dashboard:home")

    if request.method == "POST":
        try:
            client = Client.objects.get(pk=request.POST.get("client"))
        except (Client.DoesNotExist, ValueError):
            messages.error(request, "Client invalide.")
            return redirect("dashboard:recurring")
        cg = None
        cg_id = request.POST.get("caregiver")
        if cg_id:
            cg = Caregiver.objects.filter(pk=cg_id).first()
        weekdays = ",".join(request.POST.getlist("weekdays"))
        if not weekdays:
            messages.error(request, "Sélectionnez au moins un jour.")
            return redirect("dashboard:recurring")
        from datetime import datetime
        try:
            start_date = datetime.strptime(
                request.POST.get("start_date") or timezone.localdate().isoformat(),
                "%Y-%m-%d").date()
            start_time = datetime.strptime(request.POST.get("start_time") or "09:00", "%H:%M").time()
        except ValueError:
            messages.error(request, "Date ou heure invalide.")
            return redirect("dashboard:recurring")
        rs = RecurringSchedule.objects.create(
            client=client, caregiver=cg, weekdays=weekdays,
            start_time=start_time,
            duration_minutes=int(request.POST.get("duration") or 120),
            start_date=start_date,
            weeks=int(request.POST.get("weeks") or 4))
        made = rs.generate()
        log(request.user, "A créé une planification récurrente", client.code)
        messages.success(request, f"Planification créée — {made} visite(s) générée(s).")
        return redirect("dashboard:recurring")

    return render(request, "dashboard/recurring.html", {
        "schedules": RecurringSchedule.objects.select_related("client", "caregiver")[:30],
        "clients": Client.objects.filter(active=True).order_by("code"),
        "caregivers": Caregiver.objects.filter(active=True).order_by("code"),
        "weekdays": RecurringSchedule.WEEKDAYS,
        "today": timezone.localdate().isoformat(),
    })


# ---- Client & Family portal --------------------------------------------------------
def _family_client(request):
    return getattr(request.user, "linked_clients", None) and request.user.linked_clients.first()


@login_required
def family_home(request):
    """Advanced family portal home — live today status, wellbeing, next visit, care team."""
    from datetime import timedelta
    from django.db.models import Count
    from clients.models import Invoice, Message
    client = _family_client(request)
    if client is None:
        messages.info(request, "Aucun proche n'est associé à votre compte.")
        return redirect("dashboard:home")
    now = timezone.localtime()
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Today's live status (from EVV)
    todays = (client.visits.filter(scheduled_start__gte=day, scheduled_start__lt=day + timedelta(days=1))
              .exclude(status=VisitStatus.CANCELLED).select_related("caregiver").order_by("scheduled_start"))
    today_events = []
    for v in todays:
        cg = v.caregiver.full_name if v.caregiver else "Soignant"
        if v.check_out_at:
            today_events.append({"tone": "g", "time": timezone.localtime(v.check_out_at).strftime("%H:%M"),
                                 "text": f"Visite terminée — {cg}"})
        elif v.check_in_at:
            today_events.append({"tone": "b", "time": timezone.localtime(v.check_in_at).strftime("%H:%M"),
                                 "text": f"{cg} est arrivé(e) — visite en cours"})
        else:
            today_events.append({"tone": "n", "time": timezone.localtime(v.scheduled_start).strftime("%H:%M"),
                                 "text": f"Visite prévue avec {cg}"})

    upcoming = (client.visits.filter(scheduled_start__gte=now).exclude(status=VisitStatus.CANCELLED)
                .select_related("caregiver").order_by("scheduled_start"))
    next_visit = upcoming.first()
    recent_reports = (CareReport.objects.filter(visit__client=client)
                      .select_related("caregiver").order_by("-created_at")[:5])

    # Wellbeing (mood) trend — last 8 reports, oldest→newest
    mood_reports = list(CareReport.objects.filter(visit__client=client, mood__isnull=False)
                        .order_by("-created_at")[:8])[::-1]
    wellbeing = {"labels": [r.created_at.strftime("%d/%m") for r in mood_reports],
                 "moods": [r.mood * 20 for r in mood_reports]}
    avg_mood = round(sum(r.mood for r in mood_reports) / len(mood_reports) * 20) if mood_reports else None

    # Care team
    team = (client.visits.filter(status=VisitStatus.COMPLETED, caregiver__isnull=False)
            .values("caregiver__code", "caregiver__first_name", "caregiver__last_name")
            .annotate(n=Count("id")).order_by("-n")[:5])

    due = Invoice.objects.filter(client=client).exclude(status="PAID").count()
    unread = Message.objects.filter(client=client, from_agency=True, read=False).count()
    return render(request, "dashboard/family_home.html", {
        "client": client, "next_visit": next_visit, "today_events": today_events,
        "upcoming_count": upcoming.count(), "recent_reports": recent_reports,
        "wellbeing": wellbeing, "avg_mood": avg_mood, "team": team,
        "due_invoices": due, "unread_messages": unread,
    })


@login_required
def family_team(request):
    from django.db.models import Count
    client = _family_client(request)
    if client is None:
        return redirect("dashboard:home")
    team = (client.visits.filter(status=VisitStatus.COMPLETED, caregiver__isnull=False)
            .values("caregiver__id", "caregiver__code", "caregiver__first_name",
                    "caregiver__last_name", "caregiver__languages")
            .annotate(n=Count("id")).order_by("-n"))
    return render(request, "dashboard/family_team.html", {"client": client, "team": team})


@login_required
def family_documents(request):
    client = _family_client(request)
    if client is None:
        return redirect("dashboard:home")
    care_plan = getattr(client, "care_plan", None)
    assessments = client.assessments.all() if hasattr(client, "assessments") else []
    reports = (CareReport.objects.filter(visit__client=client)
               .select_related("visit", "caregiver").order_by("-created_at")[:20])
    return render(request, "dashboard/family_documents.html", {
        "client": client, "care_plan": care_plan, "assessments": assessments, "reports": reports})


@login_required
def family_schedule(request):
    client = _family_client(request)
    if client is None:
        return redirect("dashboard:home")
    now = timezone.localtime()
    upcoming = (client.visits.filter(scheduled_start__gte=now)
                .exclude(status=VisitStatus.CANCELLED)
                .select_related("caregiver").order_by("scheduled_start")[:20])
    past = (client.visits.filter(scheduled_start__lt=now, status=VisitStatus.COMPLETED)
            .select_related("caregiver").order_by("-scheduled_start")[:20])
    return render(request, "dashboard/family_schedule.html",
                  {"client": client, "upcoming": upcoming, "past": past})


@login_required
def family_reports(request):
    client = _family_client(request)
    if client is None:
        return redirect("dashboard:home")
    reports = (CareReport.objects.filter(visit__client=client)
               .select_related("caregiver", "visit").order_by("-created_at")[:40])
    return render(request, "dashboard/family_reports.html",
                  {"client": client, "reports": reports})


@login_required
def family_messages(request):
    from clients.models import Message
    client = _family_client(request)
    if client is None:
        return redirect("dashboard:home")
    if request.method == "POST":
        body = request.POST.get("body", "").strip()
        if body:
            Message.objects.create(client=client, sender=request.user,
                                   from_agency=False, body=body)
        return redirect("dashboard:family_messages")
    thread = client.messages.select_related("sender").all()
    thread.filter(from_agency=True, read=False).update(read=True)
    return render(request, "dashboard/family_messages.html",
                  {"client": client, "thread": thread})


@login_required
def family_invoices(request):
    from clients.models import Invoice
    client = _family_client(request)
    if client is None:
        return redirect("dashboard:home")
    invoices = Invoice.objects.filter(client=client)
    total_due = sum(i.amount for i in invoices if i.status != "PAID")
    return render(request, "dashboard/family_invoices.html",
                  {"client": client, "invoices": invoices, "total_due": total_due})


# ---- Care Insights: classify & triage care notes -----------------------------------
@login_required
def care_insights(request):
    """Reads every care note, classifies it (functional/medical/clinical) and ranks by
    severity so the notes needing attention surface first. Guidance, not diagnosis."""
    from django.db.models import Count, Q
    from django.db.models.functions import TruncDate
    from ai.services import CATEGORY_LABELS, SEVERITY_LABELS
    if not (request.user.is_staff or getattr(request.user, "is_coordinator", False)):
        messages.info(request, "Réservé au bureau.")
        return redirect("dashboard:home")

    qs = CareReport.objects.select_related("visit__client", "caregiver")
    # Filters
    f_client = request.GET.get("client", "").strip()
    f_cg = request.GET.get("caregiver", "").strip()
    f_from = request.GET.get("from", "").strip()
    f_to = request.GET.get("to", "").strip()
    if f_client:
        qs = qs.filter(visit__client_id=f_client)
    if f_cg:
        qs = qs.filter(caregiver_id=f_cg)
    if f_from:
        qs = qs.filter(created_at__date__gte=f_from)
    if f_to:
        qs = qs.filter(created_at__date__lte=f_to)

    view = request.GET.get("view", "list")
    ctx = {
        "view": view, "cat_labels": CATEGORY_LABELS, "sev_labels": SEVERITY_LABELS,
        "clients": Client.objects.filter(active=True).order_by("code"),
        "caregivers": Caregiver.objects.filter(active=True).order_by("code"),
        "f_client": f_client, "f_cg": f_cg, "f_from": f_from, "f_to": f_to,
        "total": qs.count(),
        "attention": qs.filter(insight_severity__gte=2).count(),
    }

    if view == "stats":
        # Category distribution
        cat_rows = qs.values("insight_category").annotate(n=Count("id"))
        cat_map = {r["insight_category"]: r["n"] for r in cat_rows}
        order = ["MEDICAL", "CLINICAL", "FUNCTIONAL", "GENERAL"]
        # Severity distribution
        sev_rows = qs.values("insight_severity").annotate(n=Count("id"))
        sev_map = {r["insight_severity"]: r["n"] for r in sev_rows}
        # Notes over last 14 days
        from django.utils import timezone as tz
        start = (tz.localtime() - tz.timedelta(days=13)).date()
        labels, keys = [], []
        for i in range(14):
            d = start + tz.timedelta(days=i)
            keys.append(d); labels.append(d.strftime("%d/%m"))
        day_rows = (qs.filter(created_at__date__gte=start)
                    .annotate(d=TruncDate("created_at")).values("d")
                    .annotate(n=Count("id"), att=Count("id", filter=Q(insight_severity__gte=2))))
        dmap = {r["d"]: r for r in day_rows}
        # Top clients / caregivers by attention notes
        top_clients = list(qs.filter(insight_severity__gte=2)
                           .values("visit__client__code")
                           .annotate(n=Count("id")).order_by("-n")[:6])
        top_cg = list(qs.filter(insight_severity__gte=2)
                      .values("caregiver__code").annotate(n=Count("id")).order_by("-n")[:6])
        ctx["stats"] = {
            "cat_labels": ["Médical", "Clinique", "Fonctionnel", "Général"],
            "cat_counts": [cat_map.get(k, 0) for k in order],
            "sev_counts": [sev_map.get(i, 0) for i in range(4)],
            "day_labels": labels,
            "day_total": [dmap.get(k, {}).get("n", 0) for k in keys],
            "day_att": [dmap.get(k, {}).get("att", 0) for k in keys],
            "top_clients": [{"code": r["visit__client__code"], "n": r["n"]} for r in top_clients],
            "top_cg": [{"code": r["caregiver__code"] or "—", "n": r["n"]} for r in top_cg],
        }
        ctx["data_json"] = ctx["stats"]
    else:
        ctx["reports"] = qs.order_by("-insight_severity", "-created_at")[:120]

    return render(request, "dashboard/insights.html", ctx)


# ---- Compliance: certification tracking + renewal alerts ----------------------------
@login_required
def compliance(request):
    """Monitor caregiver licence/certification expiry and send renewal reminders."""
    from datetime import timedelta
    from caregivers.models import Certification
    if not _office_only(request):
        messages.info(request, "Réservé au bureau.")
        return redirect("dashboard:home")
    today = timezone.localdate()
    soon = today + timedelta(days=60)

    base = Certification.objects.exclude(expires_on__isnull=True)
    qs = base.select_related("caregiver")
    status = request.GET.get("status", "").strip()
    if status == "expired":
        qs = qs.filter(expires_on__lt=today)
    elif status == "expiring":
        qs = qs.filter(expires_on__gte=today, expires_on__lte=soon)
    elif status == "valid":
        qs = qs.filter(expires_on__gt=soon)
    cg_id = request.GET.get("caregiver", "").strip()
    if cg_id:
        qs = qs.filter(caregiver_id=cg_id)

    rows = []
    for c in qs.order_by("expires_on"):
        days = (c.expires_on - today).days
        st = "expired" if days < 0 else ("expiring" if days <= 60 else "valid")
        rows.append({"cert": c, "days": days, "status": st})

    kpis = {
        "total": base.count(),
        "expiring": base.filter(expires_on__gte=today, expires_on__lte=soon).count(),
        "expired": base.filter(expires_on__lt=today).count(),
    }
    return render(request, "dashboard/compliance.html", {
        "rows": rows, "kpis": kpis, "status": status, "f_cg": cg_id,
        "caregivers": Caregiver.objects.filter(active=True).order_by("code"),
    })


def _remind_one(cert):
    from notifications.models import Notification
    if cert.caregiver.user_id:
        Notification.objects.create(
            recipient=cert.caregiver.user, level="ATTENTION",
            title="Certification à renouveler",
            body=f"Votre certification « {cert.name} » expire le "
                 f"{cert.expires_on:%d/%m/%Y}. Merci de la renouveler à temps.")
        return True
    return False


@login_required
@require_POST
def remind_cert(request, pk):
    from caregivers.models import Certification
    if not _office_only(request):
        return redirect("dashboard:home")
    cert = get_object_or_404(Certification.objects.select_related("caregiver"), pk=pk)
    sent = _remind_one(cert)
    log(request.user, "Rappel de renouvellement de certification", cert.caregiver.code)
    messages.success(request, f"Rappel envoyé à {cert.caregiver.code}." if sent
                     else f"{cert.caregiver.code} n'a pas de compte lié — rappel non envoyé.")
    return redirect("dashboard:compliance")


@login_required
@require_POST
def remind_all(request):
    from datetime import timedelta
    from caregivers.models import Certification
    if not _office_only(request):
        return redirect("dashboard:home")
    today = timezone.localdate()
    horizon = today + timedelta(days=60)
    certs = Certification.objects.filter(expires_on__lte=horizon).select_related("caregiver")
    n = sum(1 for c in certs if _remind_one(c))
    log(request.user, "Rappels de renouvellement (lot)", str(n))
    messages.success(request, f"{n} rappel(s) envoyé(s) aux soignants concernés.")
    return redirect("dashboard:compliance")


@login_required
@require_POST
def promote_applicant(request, pk):
    """Turn a Talent Hub applicant into an active caregiver."""
    from caregivers.models import Applicant, Caregiver, ApplicationStage
    if not _office_only(request):
        return redirect("dashboard:home")
    a = get_object_or_404(Applicant, pk=pk)
    if a.promoted_to:
        messages.info(request, "Ce candidat est déjà un soignant.")
        return redirect("dashboard:recruitment")
    nums = []
    for code in Caregiver.objects.values_list("code", flat=True):
        digits = "".join(ch for ch in code if ch.isdigit())
        if digits:
            nums.append(int(digits))
    new_code = f"Soignant #{(max(nums) + 1) if nums else 1:03d}"
    cg = Caregiver.objects.create(code=new_code, first_name=a.first_name,
                                  last_name=a.last_name, phone=a.phone, active=True)
    a.promoted_to = cg
    a.stage = ApplicationStage.ACTIVE
    a.save(update_fields=["promoted_to", "stage"])
    log(request.user, "A promu un candidat en soignant", new_code)
    messages.success(request, f"{a.first_name} {a.last_name} est désormais {new_code}.")
    return redirect("dashboard:recruitment")


# ---- Reports Center: operational report exports ------------------------------------
import csv as _csv


@login_required
def weekly_report_pdf(request):
    if not _office_only(request):
        return redirect("dashboard:home")
    data = pdfgen.weekly_report_pdf()
    stamp = timezone.localtime().strftime("%Y%m%d")
    return _pdf_response(data, f"rapport-hebdo-{stamp}.pdf", download="download" in request.GET)


@login_required
def timesheet_csv(request):
    if not _office_only(request):
        return redirect("dashboard:home")
    now = timezone.localtime()
    monday = (now - timezone.timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0)
    sunday = monday + timezone.timedelta(days=7)
    visits = (Visit.objects.filter(status=VisitStatus.COMPLETED,
                                   scheduled_start__gte=monday, scheduled_start__lt=sunday)
              .select_related("caregiver"))
    agg = {}
    for v in visits:
        cg = v.caregiver
        if not cg:
            continue
        hrs = ((v.check_out_at - v.check_in_at).total_seconds() / 3600
               if v.check_in_at and v.check_out_at
               else (v.scheduled_end - v.scheduled_start).total_seconds() / 3600)
        d = agg.setdefault(cg.code, {"name": cg.full_name, "hours": 0.0, "visits": 0})
        d["hours"] += hrs
        d["visits"] += 1
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="feuilles-temps-{monday:%Y%m%d}.csv"'
    w = _csv.writer(resp)
    w.writerow(["Code", "Nom", "Visites", "Heures"])
    for code, d in sorted(agg.items()):
        w.writerow([code, d["name"], d["visits"], round(d["hours"], 1)])
    return resp


@login_required
def compliance_csv(request):
    from caregivers.models import Certification
    if not _office_only(request):
        return redirect("dashboard:home")
    today = timezone.localdate()
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = 'attachment; filename="conformite-certifications.csv"'
    w = _csv.writer(resp)
    w.writerow(["Soignant", "Nom", "Certification", "Émise le", "Expire le", "Statut", "Jours restants"])
    for c in (Certification.objects.exclude(expires_on__isnull=True)
              .select_related("caregiver").order_by("expires_on")):
        days = (c.expires_on - today).days
        status = "Expirée" if days < 0 else ("Expire bientôt" if days <= 60 else "Valide")
        w.writerow([c.caregiver.code, c.caregiver.full_name, c.name,
                    c.issued_on or "", c.expires_on, status, days])
    return resp


# ============================================================================
#  Live real-time ops
# ============================================================================
@login_required
def live(request):
    if not _office_only(request):
        return redirect("dashboard:home")
    return render(request, "dashboard/live.html", {})


@login_required
def live_status(request):
    """JSON snapshot of current operations — polled by the Live page."""
    now = timezone.localtime()
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    nxt = day + timezone.timedelta(days=1)
    todays = Visit.objects.filter(scheduled_start__gte=day, scheduled_start__lt=nxt)

    in_progress = []
    for v in (Visit.objects.filter(status=VisitStatus.IN_PROGRESS)
              .select_related("client", "caregiver").order_by("check_in_at")):
        since = timezone.localtime(v.check_in_at).strftime("%H:%M") if v.check_in_at else "—"
        in_progress.append({"caregiver": v.caregiver.code if v.caregiver else "—",
                            "client": v.client.first_name, "since": since})
    late = [{"caregiver": v.caregiver.code if v.caregiver else "Non affecté",
             "client": v.client.code, "min": v.minutes_late}
            for v in todays.filter(status=VisitStatus.SCHEDULED).select_related("client", "caregiver")
            if v.minutes_late > 0]
    recent = []
    for v in (todays.filter(check_in_at__isnull=False).select_related("caregiver", "client")
              .order_by("-check_in_at")[:6]):
        recent.append({"caregiver": v.caregiver.code if v.caregiver else "—",
                       "client": v.client.code,
                       "at": timezone.localtime(v.check_in_at).strftime("%H:%M")})
    return JsonResponse({
        "in_progress": in_progress, "late": late, "recent": recent,
        "counts": {"in_progress": len(in_progress), "late": len(late),
                   "uncovered": todays.filter(status=VisitStatus.UNCOVERED).count(),
                   "completed": todays.filter(status=VisitStatus.COMPLETED).count(),
                   "scheduled": todays.exclude(status=VisitStatus.CANCELLED).count()},
        "ts": now.strftime("%H:%M:%S"),
    })


# ============================================================================
#  Billing & payroll
# ============================================================================
@login_required
def billing(request):
    if not _office_only(request):
        return redirect("dashboard:home")
    from clients.models import Invoice
    invoices = Invoice.objects.select_related("client").all()[:150]
    kpis = {
        "billed": sum(i.amount for i in Invoice.objects.all()),
        "due": sum(i.amount for i in Invoice.objects.exclude(status="PAID")),
        "paid": sum(i.amount for i in Invoice.objects.filter(status="PAID")),
    }
    # AR aging (unpaid invoices bucketed by days since due)
    today = timezone.localdate()
    aging = {"current": 0, "d30": 0, "d60": 0, "d90": 0}
    for i in Invoice.objects.exclude(status="PAID"):
        ref = i.due_date or i.issued_date
        overdue = (today - ref).days if ref else 0
        if overdue <= 0:
            aging["current"] += float(i.amount)
        elif overdue <= 30:
            aging["d30"] += float(i.amount)
        elif overdue <= 60:
            aging["d60"] += float(i.amount)
        else:
            aging["d90"] += float(i.amount)
    aging = {k: round(v) for k, v in aging.items()}

    # Client profitability: revenue (invoices) vs estimated caregiver cost (hours × avg pay)
    from django.db.models import Avg
    avg_pay = float(Caregiver.objects.filter(active=True).aggregate(a=Avg("pay_rate"))["a"] or 5)
    profit_rows = []
    for cl in Client.objects.filter(active=True).prefetch_related("invoices", "visits"):
        rev = float(sum(i.amount for i in cl.invoices.all()))
        if rev <= 0:
            continue
        hrs = sum((v.check_out_at - v.check_in_at).total_seconds() / 3600
                  if v.check_in_at and v.check_out_at
                  else (v.scheduled_end - v.scheduled_start).total_seconds() / 3600
                  for v in cl.visits.filter(status=VisitStatus.COMPLETED))
        cost = hrs * avg_pay
        margin = rev - cost
        profit_rows.append({"client": cl, "revenue": round(rev), "cost": round(cost),
                            "margin": round(margin),
                            "pct": round(100 * margin / rev) if rev else 0})
    profit_rows.sort(key=lambda r: r["margin"], reverse=True)
    # month options (last 6 months)
    months = []
    d = timezone.localdate().replace(day=1)
    for _ in range(6):
        months.append(d.strftime("%Y-%m"))
        d = (d - timezone.timedelta(days=1)).replace(day=1)
    return render(request, "dashboard/billing.html",
                  {"invoices": invoices, "kpis": kpis, "months": months, "aging": aging,
                   "profit_rows": profit_rows[:12]})


@login_required
@require_POST
def generate_invoices(request):
    from datetime import datetime
    from decimal import Decimal
    from clients.models import Client, Invoice
    if not _office_only(request):
        return redirect("dashboard:home")
    period = request.POST.get("period", "")
    try:
        year, month = map(int, period.split("-"))
        m_start = timezone.make_aware(datetime(year, month, 1))
    except (ValueError, TypeError):
        messages.error(request, "Période invalide.")
        return redirect("dashboard:billing")
    m_end = timezone.make_aware(datetime(year + (month == 12), (month % 12) + 1, 1))
    label = m_start.strftime("%B %Y").capitalize()

    made = 0
    for client in Client.objects.filter(active=True):
        if Invoice.objects.filter(client=client, period=label).exists():
            continue
        visits = client.visits.filter(status=VisitStatus.COMPLETED,
                                       scheduled_start__gte=m_start, scheduled_start__lt=m_end)
        hours = sum((v.check_out_at - v.check_in_at).total_seconds() / 3600
                    if v.check_in_at and v.check_out_at
                    else (v.scheduled_end - v.scheduled_start).total_seconds() / 3600
                    for v in visits)
        if hours <= 0:
            continue
        amount = (Decimal(str(round(hours, 1))) * client.bill_rate).quantize(Decimal("0.01"))
        Invoice.objects.create(
            client=client, period=label, hours=round(hours, 1), amount=amount,
            status=Invoice.Status.DUE, issued_date=timezone.localdate(),
            due_date=timezone.localdate() + timezone.timedelta(days=15))
        made += 1
    log(request.user, "A généré des factures", f"{made} · {label}")
    messages.success(request, f"{made} facture(s) générée(s) pour {label}.")
    return redirect("dashboard:billing")


@login_required
@require_POST
def mark_invoice_paid(request, pk):
    from clients.models import Invoice
    if not _office_only(request):
        return redirect("dashboard:home")
    inv = get_object_or_404(Invoice, pk=pk)
    inv.status = Invoice.Status.PAID
    inv.paid_on = timezone.localdate()
    inv.save(update_fields=["status", "paid_on"])
    messages.success(request, f"Facture {inv.client.code} · {inv.period} marquée payée.")
    return redirect(request.META.get("HTTP_REFERER") or "dashboard:billing")


@login_required
def payroll_csv(request):
    from datetime import datetime
    from decimal import Decimal
    if not _office_only(request):
        return redirect("dashboard:home")
    period = request.GET.get("period", timezone.localdate().strftime("%Y-%m"))
    try:
        year, month = map(int, period.split("-"))
        m_start = timezone.make_aware(datetime(year, month, 1))
    except (ValueError, TypeError):
        m_start = timezone.localtime().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    m_end = timezone.make_aware(datetime(m_start.year + (m_start.month == 12),
                                         (m_start.month % 12) + 1, 1))
    visits = (Visit.objects.filter(status=VisitStatus.COMPLETED, hours_approved=True,
                                   scheduled_start__gte=m_start, scheduled_start__lt=m_end)
              .select_related("caregiver"))
    agg = {}
    for v in visits:
        cg = v.caregiver
        if not cg:
            continue
        hrs = ((v.check_out_at - v.check_in_at).total_seconds() / 3600
               if v.check_in_at and v.check_out_at
               else (v.scheduled_end - v.scheduled_start).total_seconds() / 3600)
        d = agg.setdefault(cg.code, {"cg": cg, "hours": 0.0, "visits": 0})
        d["hours"] += hrs
        d["visits"] += 1
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="paie-{period}.csv"'
    w = _csv.writer(resp)
    w.writerow(["Code", "Nom", "Visites", "Heures", "Taux ($/h)", "Total ($)"])
    for code, d in sorted(agg.items()):
        hrs = round(d["hours"], 1)
        total = (Decimal(str(hrs)) * d["cg"].pay_rate).quantize(Decimal("0.01"))
        w.writerow([code, d["cg"].full_name, d["visits"], hrs, d["cg"].pay_rate, total])
    return resp


# ============================================================================
#  AI Copilot
# ============================================================================
@login_required
def copilot(request):
    if not _office_only(request):
        return redirect("dashboard:home")
    return render(request, "dashboard/copilot.html", {})


@login_required
@require_POST
def copilot_ask(request):
    """Answer a wide range of operations questions from live data (LLM-enhanced if a key is set)."""
    import re
    from caregivers.models import Certification, Caregiver as CG
    from scheduling.models import VisitRequest
    from clients.models import Invoice, Lead, CareConcern
    try:
        q = json.loads(request.body or "{}").get("q", "").lower().strip()
    except ValueError:
        q = ""
    now = timezone.localtime()
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = day - timezone.timedelta(days=day.weekday())
    today = Visit.objects.filter(scheduled_start__gte=day,
                                 scheduled_start__lt=day + timezone.timedelta(days=1))

    def has(*words):
        return any(w in q for w in words)

    def hours_for(cg, since):
        return round(sum((v.check_out_at - v.check_in_at).total_seconds() / 3600
                         for v in cg.visits.filter(status=VisitStatus.COMPLETED, scheduled_start__gte=since)
                         if v.check_in_at and v.check_out_at), 1)

    def answer():
        # --- specific client lookup: "client #014" ---
        m = re.search(r"client\s*#?\s*(\d+)", q)
        if m and has("client", "statut", "état", "info", "prochaine", "s'occupe", "soignant") \
                and not has("meilleur", "recommand", "affecter"):
            code = f"Client #{int(m.group(1)):03d}"
            c = Client.objects.filter(code=code).first()
            if c:
                nxt = c.visits.filter(scheduled_start__gte=now).order_by("scheduled_start").first()
                done = c.visits.filter(status=VisitStatus.COMPLETED).count()
                openc = c.concerns.exclude(status="RESOLVED").count() if hasattr(c, "concerns") else 0
                parts = [f"{c.code} — {c.full_name} · {c.care_type or 'soins'} · risque {c.risk_level.lower()}",
                         f"{done} visite(s) réalisées, {openc} suivi(s) clinique(s) actif(s)."]
                if nxt:
                    parts.append(f"Prochaine visite : {timezone.localtime(nxt.scheduled_start):%d/%m %H:%M}"
                                 f" avec {nxt.caregiver.code if nxt.caregiver else 'non affecté'}.")
                return "\n".join(parts)
            return f"Aucun client {code} trouvé."

        # --- specific caregiver lookup: "soignant #007" ---
        m = re.search(r"soignant\s*#?\s*(\d+)", q)
        if m:
            code = f"Soignant #{int(m.group(1)):03d}"
            cg = CG.objects.filter(code=code).first()
            if cg:
                hrs = hours_for(cg, week_start)
                nxt = cg.visits.filter(scheduled_start__gte=now).order_by("scheduled_start").first()
                certs = cg.certifications.filter(expires_on__lt=timezone.localdate()).count()
                out = [f"{cg.code} — {cg.full_name} · ponctualité {cg.punctuality_score}% · {hrs} h cette semaine."]
                if nxt:
                    out.append(f"Prochaine visite : {timezone.localtime(nxt.scheduled_start):%d/%m %H:%M} ({nxt.client.code}).")
                if certs:
                    out.append(f"⚠️ {certs} certification(s) expirée(s).")
                return "\n".join(out)
            return f"Aucun {code} trouvé."

        # --- best caregiver for a client ---
        if has("meilleur", "recommand", "qui affecter", "best") and re.search(r"client\s*#?\s*\d+", q):
            code = f"Client #{int(re.search(r'client\s*#?\s*(\d+)', q).group(1)):03d}"
            v = Visit.objects.filter(client__code=code, status=VisitStatus.UNCOVERED).first() \
                or Visit.objects.filter(client__code=code, scheduled_start__gte=now).first()
            if v:
                from ai.services import carematch_ranked
                top = carematch_ranked(v, top_n=3)
                if top:
                    lines = [f"• {t['caregiver'].code} — {t['score']}% ({t['continuity_visits']} visite(s), {t['arrival']['confidence']}% arrivée)" for t in top]
                    return f"Meilleurs profils pour {code} :\n" + "\n".join(lines)
            return f"Aucune visite à pourvoir pour {code}."

        if has("retard", "late", "en retard"):
            late = [v for v in today.select_related("client", "caregiver") if v.minutes_late > 0]
            if not late:
                return "Aucun soignant en retard pour le moment. 👍"
            lines = [f"• {v.caregiver.code if v.caregiver else 'Non affecté'} — {v.minutes_late} min ({v.client.code})" for v in late[:8]]
            return f"{len(late)} soignant(s) en retard aujourd'hui :\n" + "\n".join(lines)

        if has("non couvert", "ouvert", "uncovered", "à couvrir", "à pourvoir"):
            unc = today.filter(status=VisitStatus.UNCOVERED).select_related("client")
            n = unc.count()
            if not n:
                return "Toutes les visites du jour sont couvertes. ✅"
            lines = [f"• {v.client.code} — {timezone.localtime(v.scheduled_start):%H:%M}" for v in unc[:8]]
            return f"{n} visite(s) non couverte(s) :\n" + "\n".join(lines) + "\n\nUtilisez « Auto-remplir » pour les affecter."

        if has("revenu", "chiffre", "facturé", "encaisser", "encaissé", "impayé", "impaye", "payé", "argent", "recette", "billing", "facturation"):
            billed = sum(i.amount for i in Invoice.objects.all())
            paid = sum(i.amount for i in Invoice.objects.filter(status="PAID"))
            due = sum(i.amount for i in Invoice.objects.exclude(status="PAID"))
            return (f"Facturation : {billed:.0f} $ facturés au total · {paid:.0f} $ encaissés · "
                    f"{due:.0f} $ à encaisser (non payées).")

        if has("client") and has("combien", "nombre", "actifs", "total"):
            return f"{Client.objects.filter(active=True).count()} clients actifs."
        if has("nouveau", "nouveaux") and has("client"):
            m0 = day.replace(day=1)
            return f"{Client.objects.filter(created_at__gte=m0).count()} nouveau(x) client(s) ce mois-ci."
        if has("risque", "départ", "depart", "churn", "partir", "quitter", "prédiction", "prediction"):
            from ai.services import churn_ranked
            rows = churn_ranked(6)
            if not rows:
                return "Aucun client à risque de départ détecté. Clientèle stable ✅"
            lines = [f"• {r['client'].code} — risque {r['score']}/100 ({', '.join(r['factors']) or '—'})" for r in rows]
            return "Clients à risque de départ (prédiction) :\n" + "\n".join(lines)

        if has("soignant", "caregiver") and has("combien", "nombre", "actifs", "disponible"):
            active = CG.objects.filter(active=True).count()
            on_visit = Visit.objects.filter(status=VisitStatus.IN_PROGRESS).values("caregiver").distinct().count()
            return f"{active} soignants actifs · {on_visit} en visite actuellement · {active - on_visit} disponibles."

        if has("certif", "expir", "conform"):
            soon = timezone.localdate() + timezone.timedelta(days=60)
            exp = Certification.objects.filter(expires_on__lt=timezone.localdate()).count()
            near = Certification.objects.filter(expires_on__gte=timezone.localdate(), expires_on__lte=soon).count()
            return f"Conformité : {exp} certification(s) expirée(s) et {near} expirant sous 60 jours. Voir « Conformité »."

        if has("incident"):
            n = Incident.objects.exclude(status=IncidentStatus.RESOLVED).count()
            crit = Incident.objects.filter(severity="CRITICAL").exclude(status=IncidentStatus.RESOLVED).count()
            return f"{n} incident(s) ouvert(s), dont {crit} critique(s)."

        if has("demande", "request", "approuver", "approbation"):
            n = VisitRequest.objects.filter(status="PENDING").count()
            return f"{n} demande(s) de visite en attente d'approbation. Voir « Demandes de visites »."

        if has("prospect", "lead", "recommandation", "pipeline"):
            total = Lead.objects.exclude(stage="LOST").count()
            new_l = Lead.objects.filter(stage="NEW").count()
            conv = Lead.objects.filter(stage="CONVERTED").count()
            return f"CRM : {total} prospect(s) dans le pipeline · {new_l} nouveau(x) · {conv} converti(s)."

        if has("clinique", "plaie", "suivi", "escarre"):
            n = CareConcern.objects.exclude(status="RESOLVED").count()
            return f"{n} suivi(s) clinique(s) actif(s). Voir « Suivi clinique »."

        if has("heure", "top", "meilleur", "performance", "hours", "actif", "productif"):
            load = []
            for cg in CG.objects.filter(active=True).prefetch_related("visits"):
                h = hours_for(cg, day - timezone.timedelta(days=7))
                if h:
                    load.append((cg.code, h))
            load.sort(key=lambda x: x[1], reverse=True)
            lines = [f"• {c} — {h} h" for c, h in load[:5]]
            return "Soignants les plus actifs (7 j) :\n" + "\n".join(lines)

        if has("semaine", "week"):
            wv = Visit.objects.filter(scheduled_start__gte=week_start,
                                      scheduled_start__lt=week_start + timezone.timedelta(days=7))
            return (f"Cette semaine : {wv.exclude(status=VisitStatus.CANCELLED).count()} visites planifiées, "
                    f"{wv.filter(status=VisitStatus.COMPLETED).count()} terminées, "
                    f"{wv.filter(status=VisitStatus.UNCOVERED).count()} non couvertes.")

        if has("prévoir", "prevoir", "prévision", "prevision", "forecast", "capacité", "capacite", "besoin"):
            from ai.services import demand_forecast
            f = demand_forecast(7)
            return (f"Prévision 7 jours : {f['upcoming']} visites prévues, capacité estimée {f['capacity']}, "
                    f"{f['uncovered']} déjà non couvertes." + (f" Risque de sous-effectif : {f['gap']}." if f['gap'] else ""))

        if has("aujourd", "today", "visite", "combien", "état", "resume", "résumé", "situation", "point"):
            b = daily_brief()
            return (f"Aujourd'hui : {today.exclude(status=VisitStatus.CANCELLED).count()} visites, "
                    f"{b['completed']} terminées, {b['late']} en retard, {b['uncovered']} non couvertes "
                    f"({b['on_schedule_pct']}% dans les temps).")

        if has("bonjour", "salut", "hello", "coucou", "bonsoir"):
            return "Bonjour ! Posez-moi une question : clients, soignants, visites, revenus, incidents, conformité, prévisions…"
        if has("merci", "thanks"):
            return "Avec plaisir ! 🙂 Autre chose ?"
        if has("aide", "help", "peux-tu", "que sais", "capacité"):
            return ("Je peux répondre sur : l'état du jour, les retards, les visites non couvertes, "
                    "les revenus/facturation, les clients (actifs, nouveaux, à risque), les soignants "
                    "(disponibles, plus actifs), la conformité, les incidents, les demandes, le CRM, "
                    "les prévisions, un client précis (« client #014 ») ou un soignant précis (« soignant #007 »).")

        try:
            from ai import llm
            if llm.available():
                b = daily_brief()
                ctx = (f"Données du jour: {today.exclude(status=VisitStatus.CANCELLED).count()} visites, "
                       f"{b['completed']} terminées, {b['late']} en retard, {b['uncovered']} non couvertes, "
                       f"{Client.objects.filter(active=True).count()} clients, "
                       f"{CG.objects.filter(active=True).count()} soignants.")
                out = llm.complete(f"{ctx}\nQuestion du coordinateur: {q}\nRéponds brièvement en français, sans inventer de chiffres.",
                                   system="Tu es le copilote IA d'une agence de soins à domicile.", max_tokens=220)
                if out:
                    return out.strip()
        except Exception:
            pass

        return ("Je n'ai pas bien saisi. Essayez par exemple : « revenus du mois », « clients à risque », "
                "« soignant #007 », « visites cette semaine », « prévisions », ou « état du jour ».")

    return JsonResponse({"answer": answer()})


@login_required
@require_POST
def autofill_shifts(request):
    """Assign the best available caregiver to each uncovered visit (AI Copilot action)."""
    if not _office_only(request):
        return redirect("dashboard:home")
    now = timezone.localtime()
    horizon = now + timezone.timedelta(days=7)
    uncovered = Visit.objects.filter(status=VisitStatus.UNCOVERED,
                                     scheduled_start__gte=now, scheduled_start__lt=horizon)
    filled = 0
    for v in uncovered.select_related("client"):
        matches = match_caregivers(v, top_n=1)
        if matches:
            v.caregiver = matches[0]["caregiver"]
            v.status = VisitStatus.SCHEDULED
            v.save(update_fields=["caregiver", "status"])
            filled += 1
    log(request.user, "Auto-remplissage des visites ouvertes", str(filled))
    messages.success(request, f"{filled} visite(s) affectée(s) automatiquement par l'IA.")
    return redirect("dashboard:copilot")


# ============================================================================
#  Communications (broadcast: in-app + email + SMS)
# ============================================================================
@login_required
def communications(request):
    from accounts.models import User, Role
    from notifications.services import notify
    from notifications.models import AlertLevel
    if not _office_only(request):
        return redirect("dashboard:home")

    if request.method == "POST":
        audience = request.POST.get("audience", "caregivers")
        title = request.POST.get("title", "").strip()
        body = request.POST.get("body", "").strip()
        use_email = request.POST.get("email") == "on"
        use_sms = request.POST.get("sms") == "on"
        if not title:
            messages.error(request, "Le titre est requis.")
            return redirect("dashboard:communications")
        recipients = []
        if audience == "caregivers":
            recipients = list(User.objects.filter(role=Role.CAREGIVER))
        elif audience == "families":
            recipients = list(User.objects.filter(role=Role.FAMILY))
        elif audience.startswith("cg:"):
            recipients = list(User.objects.filter(caregiver_profile__id=audience[3:]))
        n = 0
        for u in recipients:
            notify(u, title, body, level=AlertLevel.INFO, email=use_email, sms=use_sms)
            n += 1
        chans = "in-app" + (" + e-mail" if use_email else "") + (" + SMS" if use_sms else "")
        log(request.user, "Diffusion de communication", f"{n} · {chans}")
        messages.success(request, f"Message envoyé à {n} destinataire(s) ({chans}).")
        return redirect("dashboard:communications")

    from caregivers.models import Caregiver
    return render(request, "dashboard/communications.html", {
        "caregivers": Caregiver.objects.filter(active=True, user__isnull=False).order_by("code"),
        "sms_enabled": bool(getattr(settings, "TWILIO_ACCOUNT_SID", "")),
        "n_caregivers": User.objects.filter(role=Role.CAREGIVER).count(),
        "n_families": User.objects.filter(role=Role.FAMILY).count(),
    })


# ============================================================================
#  Clinical tracking — wound / care-concern manager
# ============================================================================
@login_required
def clinical(request):
    from clients.models import CareConcern
    if not _office_only(request):
        return redirect("dashboard:home")
    if request.method == "POST":
        try:
            client = Client.objects.get(pk=request.POST.get("client"))
        except (Client.DoesNotExist, ValueError):
            messages.error(request, "Client invalide.")
            return redirect("dashboard:clinical")
        c = CareConcern.objects.create(
            client=client, concern_type=request.POST.get("concern_type", "WOUND"),
            location=request.POST.get("location", "").strip(),
            description=request.POST.get("description", "").strip(),
            severity=int(request.POST.get("severity") or 2),
            opened_on=timezone.localdate(), created_by=request.user)
        log(request.user, "A ouvert un suivi clinique", client.code)
        messages.success(request, "Suivi clinique créé.")
        return redirect("dashboard:concern_detail", pk=c.id)

    status = request.GET.get("status", "active")
    qs = CareConcern.objects.select_related("client").prefetch_related("updates")
    if status == "active":
        qs = qs.exclude(status="RESOLVED")
    elif status == "resolved":
        qs = qs.filter(status="RESOLVED")
    return render(request, "dashboard/clinical.html", {
        "concerns": qs, "status": status,
        "active": CareConcern.objects.exclude(status="RESOLVED").count(),
        "resolved": CareConcern.objects.filter(status="RESOLVED").count(),
        "clients": Client.objects.filter(active=True).order_by("code"),
        "types": CareConcern.Type.choices,
    })


@login_required
def concern_detail(request, pk):
    from clients.models import CareConcern
    if not _office_only(request):
        return redirect("dashboard:home")
    concern = get_object_or_404(CareConcern.objects.select_related("client"), pk=pk)
    if request.method == "POST":
        note = request.POST.get("note", "").strip()
        new_status = request.POST.get("status", concern.status)
        if note:
            concern.updates.create(note=note, measurement=request.POST.get("measurement", "").strip(),
                                   status=new_status, created_by=request.user)
            concern.status = new_status
            if new_status == "RESOLVED" and not concern.resolved_on:
                concern.resolved_on = timezone.localdate()
            concern.save(update_fields=["status", "resolved_on"])
            messages.success(request, "Mise à jour ajoutée.")
        return redirect("dashboard:concern_detail", pk=pk)
    return render(request, "dashboard/concern_detail.html", {
        "concern": concern, "updates": concern.updates.select_related("created_by"),
        "statuses": CareConcern.Status.choices,
    })


# ============================================================================
#  Profitability / margin calculator (PDGM-style)
# ============================================================================
@login_required
def margin(request):
    if not _office_only(request):
        return redirect("dashboard:home")
    from django.db.models import Avg
    avg_bill = Client.objects.filter(active=True).aggregate(a=Avg("bill_rate"))["a"] or 8
    avg_pay = Caregiver.objects.filter(active=True).aggregate(a=Avg("pay_rate"))["a"] or 5
    return render(request, "dashboard/margin.html",
                  {"avg_bill": round(float(avg_bill), 2), "avg_pay": round(float(avg_pay), 2)})


# ============================================================================
#  Time clock (staff sign-in / sign-out) + attendance report
# ============================================================================
@login_required
def timeclock(request):
    """Self-service time clock: the logged-in user signs in / signs out."""
    from accounts.models import TimeEntry
    open_entry = request.user.time_entries.filter(clock_out__isnull=True).first()
    entries = request.user.time_entries.all()[:20]
    total_week = 0.0
    week_start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0) \
        - timezone.timedelta(days=timezone.localtime().weekday())
    for e in request.user.time_entries.filter(clock_in__gte=week_start):
        if e.hours:
            total_week += e.hours
    return render(request, "dashboard/timeclock.html", {
        "open_entry": open_entry, "entries": entries,
        "week_hours": round(total_week, 1),
        "is_office": _office_only(request),
    })


@login_required
@require_POST
def timeclock_punch(request):
    from accounts.models import TimeEntry
    open_entry = request.user.time_entries.filter(clock_out__isnull=True).first()
    if open_entry:
        open_entry.clock_out = timezone.now()
        open_entry.save(update_fields=["clock_out"])
        messages.success(request, "Sortie pointée. Bonne fin de journée !")
    else:
        TimeEntry.objects.create(user=request.user, clock_in=timezone.now())
        messages.success(request, "Entrée pointée. Bonne journée de travail !")
    return redirect("dashboard:timeclock")


@login_required
def attendance(request):
    """Team attendance report — coordinators/admins see and adjust everyone's times."""
    from accounts.models import TimeEntry, User
    if not _office_only(request):
        messages.info(request, "Réservé au bureau.")
        return redirect("dashboard:timeclock")
    qs = TimeEntry.objects.select_related("user", "adjusted_by")
    f_user = request.GET.get("user", "").strip()
    f_date = request.GET.get("date", "").strip()
    if f_user:
        qs = qs.filter(user_id=f_user)
    if f_date:
        qs = qs.filter(clock_in__date=f_date)
    entries = list(qs[:200])
    total = round(sum(e.hours for e in entries if e.hours), 1)
    return render(request, "dashboard/attendance.html", {
        "entries": entries, "total": total,
        "open_count": TimeEntry.objects.filter(clock_out__isnull=True).count(),
        "users": User.objects.order_by("username"),
        "f_user": f_user, "f_date": f_date,
    })


@login_required
@require_POST
def edit_time(request, pk):
    """Admin/coordinator adjusts a staff member's recorded clock-in/out times."""
    from datetime import datetime
    from accounts.models import TimeEntry
    if not _office_only(request):
        return redirect("dashboard:home")
    e = get_object_or_404(TimeEntry, pk=pk)

    def _dt(name):
        v = request.POST.get(name, "").strip()
        if not v:
            return None
        try:
            return timezone.make_aware(datetime.strptime(v, "%Y-%m-%dT%H:%M"))
        except ValueError:
            return None

    ci = _dt("clock_in")
    co = _dt("clock_out")
    if ci:
        e.clock_in = ci
    e.clock_out = co  # may be cleared
    e.adjusted = True
    e.adjusted_by = request.user
    e.save()
    log(request.user, "A ajusté un pointage", str(e.user))
    messages.success(request, f"Pointage de {e.user} mis à jour.")
    return redirect("dashboard:attendance")


# ============================================================================
#  Marketing / CRM — leads pipeline (LEAD → CLIENT)
# ============================================================================
@login_required
def leads(request):
    from clients.models import Lead
    if not _office_only(request):
        return redirect("dashboard:home")
    if request.method == "POST":
        Lead.objects.create(
            name=request.POST.get("name", "").strip() or "Prospect",
            phone=request.POST.get("phone", "").strip(),
            email=request.POST.get("email", "").strip(),
            source=request.POST.get("source", "REFERRAL"),
            referred_by=request.POST.get("referred_by", "").strip(),
            care_need=request.POST.get("care_need", "").strip(),
            notes=request.POST.get("notes", "").strip())
        log(request.user, "A ajouté un prospect", request.POST.get("name", ""))
        messages.success(request, "Prospect ajouté au pipeline.")
        return redirect("dashboard:leads")

    stages = []
    for key, label in Lead.Stage.choices:
        items = list(Lead.objects.filter(stage=key))
        stages.append({"key": key, "label": label, "items": items, "count": len(items)})
    total = Lead.objects.exclude(stage="LOST").count()
    converted = Lead.objects.filter(stage="CONVERTED").count()
    rate = round(100 * converted / total) if total else 0
    return render(request, "dashboard/leads.html", {
        "stages": stages, "sources": Lead.Source.choices,
        "total": Lead.objects.count(),
        "new_leads": Lead.objects.filter(stage="NEW").count(),
        "converted": converted, "rate": rate,
    })


@login_required
@require_POST
def lead_stage(request, pk):
    from clients.models import Lead
    if not _office_only(request):
        return redirect("dashboard:home")
    lead = get_object_or_404(Lead, pk=pk)
    stage = request.POST.get("stage")
    if stage in dict(Lead.Stage.choices):
        lead.stage = stage
        lead.save(update_fields=["stage"])
    return redirect("dashboard:leads")


@login_required
@require_POST
def convert_lead(request, pk):
    """Turn a prospect into an active client (LEAD → CLIENT)."""
    from clients.models import Lead
    if not _office_only(request):
        return redirect("dashboard:home")
    lead = get_object_or_404(Lead, pk=pk)
    if lead.converted_client:
        messages.info(request, "Ce prospect est déjà un client.")
        return redirect("dashboard:leads")
    nums = []
    for code in Client.objects.values_list("code", flat=True):
        d = "".join(ch for ch in code if ch.isdigit())
        if d:
            nums.append(int(d))
    parts = lead.name.split(" ", 1)
    client = Client.objects.create(
        code=f"Client #{(max(nums) + 1) if nums else 1:03d}",
        first_name=parts[0], last_name=parts[1] if len(parts) > 1 else "",
        care_type=lead.care_need or "Soins à domicile", active=True)
    lead.stage = Lead.Stage.CONVERTED
    lead.converted_client = client
    lead.save(update_fields=["stage", "converted_client"])
    log(request.user, "A converti un prospect en client", client.code)
    messages.success(request, f"{lead.name} est désormais {client.code}.")
    return redirect("dashboard:client_360", pk=client.id)


# ============================================================================
#  EVV → hours approval → payroll workflow
# ============================================================================
@login_required
def hours_approval(request):
    """Verify EVV visits and approve their hours for timesheets/payroll."""
    if not _office_only(request):
        messages.info(request, "Réservé au bureau.")
        return redirect("dashboard:home")
    pending = (Visit.objects.filter(status=VisitStatus.COMPLETED, hours_approved=False)
               .select_related("client", "caregiver").order_by("-scheduled_start")[:100])
    rows = []
    for v in pending:
        if v.check_in_at and v.check_out_at:
            hrs = round((v.check_out_at - v.check_in_at).total_seconds() / 3600, 2)
        else:
            hrs = round((v.scheduled_end - v.scheduled_start).total_seconds() / 3600, 2)
        rows.append({"visit": v, "hours": hrs})
    approved_ct = Visit.objects.filter(status=VisitStatus.COMPLETED, hours_approved=True).count()
    return render(request, "dashboard/hours_approval.html",
                  {"rows": rows, "pending_ct": len(rows), "approved_ct": approved_ct})


@login_required
@require_POST
def approve_hours(request, pk):
    if not _office_only(request):
        return redirect("dashboard:home")
    v = get_object_or_404(Visit, pk=pk)
    v.hours_approved = True
    v.save(update_fields=["hours_approved"])
    log(request.user, "A approuvé les heures d'une visite", v.client.code)
    messages.success(request, "Heures approuvées — prêtes pour la paie.")
    return redirect("dashboard:hours_approval")


@login_required
@require_POST
def approve_hours_all(request):
    if not _office_only(request):
        return redirect("dashboard:home")
    n = Visit.objects.filter(status=VisitStatus.COMPLETED, hours_approved=False).update(
        hours_approved=True)
    log(request.user, "A approuvé toutes les heures en attente", str(n))
    messages.success(request, f"{n} visite(s) approuvée(s) pour la paie.")
    return redirect("dashboard:hours_approval")


def _management_intelligence():
    """Answers the key management questions for the BI panel."""
    from datetime import timedelta
    from django.db.models import Avg, Count
    from clients.models import Invoice
    now = timezone.localtime()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    prev_month_end = month_start - timedelta(seconds=1)
    prev_month_start = prev_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    avg_pay = float(Caregiver.objects.filter(active=True).aggregate(a=Avg("pay_rate"))["a"] or 5)

    # Most profitable clients
    profit = []
    for cl in Client.objects.filter(active=True).prefetch_related("invoices", "visits"):
        rev = float(sum(i.amount for i in cl.invoices.all()))
        if rev <= 0:
            continue
        hrs = sum((v.check_out_at - v.check_in_at).total_seconds() / 3600
                  if v.check_in_at and v.check_out_at
                  else (v.scheduled_end - v.scheduled_start).total_seconds() / 3600
                  for v in cl.visits.filter(status=VisitStatus.COMPLETED))
        profit.append({"code": cl.code, "margin": round(rev - hrs * avg_pay)})
    profit.sort(key=lambda r: r["margin"], reverse=True)

    # Underutilized caregivers (fewest hours over last 14 days, among active)
    util = []
    since = now - timedelta(days=14)
    for cg in Caregiver.objects.filter(active=True).prefetch_related("visits"):
        hrs = sum((v.check_out_at - v.check_in_at).total_seconds() / 3600
                  for v in cg.visits.filter(status=VisitStatus.COMPLETED, scheduled_start__gte=since)
                  if v.check_in_at and v.check_out_at)
        util.append({"code": cg.code, "hours": round(hrs, 1)})
    util.sort(key=lambda r: r["hours"])

    # Missed visits this month (scheduled, past, never checked in)
    missed = Visit.objects.filter(status=VisitStatus.SCHEDULED, scheduled_end__lt=now,
                                  scheduled_start__gte=month_start, check_in_at__isnull=True).count()
    # Revenue this vs last month
    rev_this = float(sum(i.amount for i in Invoice.objects.filter(issued_date__gte=month_start.date())))
    rev_prev = float(sum(i.amount for i in Invoice.objects.filter(
        issued_date__gte=prev_month_start.date(), issued_date__lt=month_start.date())))
    rev_delta = round(100 * (rev_this - rev_prev) / rev_prev) if rev_prev else 0

    # At-risk clients: open incidents OR no visit in 21 days
    at_risk = []
    for cl in Client.objects.filter(active=True).prefetch_related("visits", "incidents"):
        open_inc = cl.incidents.exclude(status="RESOLVED").count() if hasattr(cl, "incidents") else 0
        last = cl.visits.order_by("-scheduled_start").first()
        stale = last and (now - last.scheduled_start).days > 21
        if open_inc or stale:
            reason = "incident ouvert" if open_inc else "sans visite récente"
            at_risk.append({"code": cl.code, "reason": reason})

    return {
        "top_profit": profit[:5],
        "underutilized": util[:5],
        "missed_month": missed,
        "rev_this": round(rev_this), "rev_delta": rev_delta,
        "at_risk": at_risk[:6], "at_risk_ct": len(at_risk),
    }


@login_required
@require_POST
def create_assessment(request, pk):
    """Record a client needs assessment; when completed, it updates the client's
    risk level and care type — feeding the care plan (CLIENT → ASSESSMENT → CARE PLAN)."""
    from datetime import datetime
    from clients.models import ClientAssessment
    if not _office_only(request):
        return redirect("dashboard:home")
    client = get_object_or_404(Client, pk=pk)
    try:
        adate = datetime.strptime(request.POST.get("assessed_on"), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        adate = timezone.localdate()
    a = ClientAssessment.objects.create(
        client=client, assessed_on=adate, assessor=request.user,
        mobility=request.POST.get("mobility", "ASSISTED"),
        cognition=request.POST.get("cognition", "NORMAL"),
        fall_risk=request.POST.get("fall_risk", "LOW"),
        adl_needs=", ".join(request.POST.getlist("adl_needs")),
        medical_notes=request.POST.get("medical_notes", "").strip(),
        recommended_hours=request.POST.get("recommended_hours") or 10,
        recommended_care_type=request.POST.get("recommended_care_type", "").strip(),
        status=request.POST.get("status", "DRAFT"))
    # A completed assessment informs the client record (→ care plan)
    if a.status == "COMPLETED":
        if a.recommended_care_type:
            client.care_type = a.recommended_care_type
        client.risk_level = {"LOW": "LOW", "MEDIUM": "MEDIUM", "HIGH": "HIGH"}.get(a.fall_risk, "LOW")
        client.save(update_fields=["care_type", "risk_level"])
    log(request.user, "A réalisé une évaluation", client.code)
    messages.success(request, "Évaluation enregistrée." + (
        " Le dossier client a été mis à jour." if a.status == "COMPLETED" else ""))
    return redirect("dashboard:client_360", pk=pk)


@login_required
@require_POST
def pay_invoice(request, pk):
    """Family online payment — marks the invoice paid; reflects everywhere instantly."""
    from clients.models import Invoice
    client = _family_client(request)
    if client is None:
        return redirect("dashboard:home")
    inv = get_object_or_404(Invoice, pk=pk, client=client)
    inv.status = Invoice.Status.PAID
    inv.paid_on = timezone.localdate()
    inv.save(update_fields=["status", "paid_on"])
    # Notify the office so every section stays in sync
    from notifications.models import Notification, AlertLevel
    from accounts.models import User, Role
    for u in User.objects.filter(role=Role.COORDINATOR)[:5]:
        Notification.objects.create(recipient=u, level=AlertLevel.INFO,
                                    title="Paiement reçu",
                                    body=f"{client.first_name} a réglé la facture {inv.period} ({inv.amount} $).")
    log(request.user, "Paiement en ligne famille", f"{client.code} · {inv.period}")
    messages.success(request, f"Paiement de {inv.amount} $ confirmé. Merci !")
    return redirect("dashboard:family_invoices")


# ============================================================================
#  Automations page (rules engine) + Connected exports
# ============================================================================
@login_required
def automations(request):
    if not _office_only(request):
        messages.info(request, "Réservé au bureau.")
        return redirect("dashboard:home")
    if request.method == "POST":
        from dashboard.management.commands.run_automations import run_rules
        s = run_rules(force_invoices=request.POST.get("force_invoices") == "1")
        log(request.user, "A exécuté les automatisations", str(s))
        messages.success(request,
            f"Automatisations exécutées : {s['cert_reminders']} rappels de certification, "
            f"{s['uncovered_alerts']} alertes de visite, {s['overdue_flagged']} factures en retard, "
            f"{s['invoices_generated']} factures générées.")
        return redirect("dashboard:automations")
    return render(request, "dashboard/automations.html", {})


@login_required
def accounting_csv(request):
    """Connected: export invoices in an accounting-friendly CSV (QuickBooks-style)."""
    from clients.models import Invoice
    if not _office_only(request):
        return redirect("dashboard:home")
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = 'attachment; filename="comptabilite-factures.csv"'
    w = _csv.writer(resp)
    w.writerow(["InvoiceNo", "Customer", "InvoiceDate", "DueDate", "Period",
                "Hours", "Amount", "Status", "PaidDate"])
    for i, inv in enumerate(Invoice.objects.select_related("client").all(), 1):
        w.writerow([f"INV-{inv.id:05d}", inv.client.code, inv.issued_date,
                    inv.due_date or "", inv.period, inv.hours, inv.amount,
                    inv.get_status_display(), inv.paid_on or ""])
    return resp


def _ics(caregiver):
    from scheduling.models import Visit, VisitStatus
    now = timezone.localtime()
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Panther Home Care//FR",
             "CALSCALE:GREGORIAN", f"X-WR-CALNAME:Panther — {caregiver.code}"]
    for v in caregiver.visits.filter(scheduled_start__gte=now - timezone.timedelta(days=7)
                                     ).exclude(status=VisitStatus.CANCELLED).select_related("client")[:200]:
        s = timezone.localtime(v.scheduled_start).strftime("%Y%m%dT%H%M%S")
        e = timezone.localtime(v.scheduled_end).strftime("%Y%m%dT%H%M%S")
        lines += ["BEGIN:VEVENT", f"UID:panther-{v.id}@panthergroup.cd",
                  f"DTSTART:{s}", f"DTEND:{e}",
                  f"SUMMARY:Visite {v.client.first_name} ({v.client.care_type or 'soins'})",
                  "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


def caregiver_calendar(request, token):
    """Connected: subscribable iCalendar feed of a caregiver's visits (no login)."""
    from caregivers.models import Caregiver
    caregiver = get_object_or_404(Caregiver, calendar_token=token)
    resp = HttpResponse(_ics(caregiver), content_type="text/calendar")
    resp["Content-Disposition"] = f'inline; filename="panther-{caregiver.code}.ics"'
    return resp


# ============================================================================
#  In-app creation — add a client / add a caregiver (staff)
# ============================================================================
import random as _random
_CITY = (-11.66, 27.48)  # Lubumbashi


def _next_code(model, prefix):
    nums = []
    for code in model.objects.values_list("code", flat=True):
        d = "".join(ch for ch in code if ch.isdigit())
        if d:
            nums.append(int(d))
    return f"{prefix} #{(max(nums) + 1) if nums else 1:03d}"


@login_required
def client_new(request):
    from accounts.models import AgencySettings
    if not _office_only(request):
        messages.info(request, "Réservé au bureau.")
        return redirect("dashboard:home")
    cfg = AgencySettings.get()
    if request.method == "POST":
        first = request.POST.get("first_name", "").strip()
        last = request.POST.get("last_name", "").strip()
        if not first:
            messages.error(request, "Le prénom est requis.")
            return redirect("dashboard:client_new")
        client = Client.objects.create(
            code=_next_code(Client, "Client"),
            first_name=first, last_name=last,
            care_type=request.POST.get("care_type", "").strip(),
            risk_level=request.POST.get("risk_level", "LOW"),
            preferred_language=request.POST.get("preferred_language", "").strip(),
            address=request.POST.get("address", "").strip(),
            latitude=_CITY[0] + _random.uniform(-0.05, 0.05),
            longitude=_CITY[1] + _random.uniform(-0.05, 0.05),
            bill_rate=request.POST.get("bill_rate") or cfg.default_bill_rate,
            has_pets=request.POST.get("has_pets") == "on",
            smoking_household=request.POST.get("smoking_household") == "on",
            notes=request.POST.get("notes", "").strip(), active=True)
        log(request.user, "A ajouté un client", client.code)
        messages.success(request, f"Client créé : {client.code} — {client.full_name}.")
        return redirect("dashboard:client_360", pk=client.id)
    return render(request, "dashboard/client_new.html", {"cfg": cfg})


@login_required
def caregiver_new(request):
    from accounts.models import AgencySettings, User, Role
    from caregivers.models import Caregiver, Skill
    if not _office_only(request):
        messages.info(request, "Réservé au bureau.")
        return redirect("dashboard:home")
    cfg = AgencySettings.get()
    if request.method == "POST":
        first = request.POST.get("first_name", "").strip()
        last = request.POST.get("last_name", "").strip()
        if not first:
            messages.error(request, "Le prénom est requis.")
            return redirect("dashboard:caregiver_new")
        cg = Caregiver.objects.create(
            code=_next_code(Caregiver, "Soignant"),
            first_name=first, last_name=last,
            phone=request.POST.get("phone", "").strip(),
            languages=request.POST.get("languages", "").strip(),
            gender=request.POST.get("gender", "U"),
            reliability_score=int(request.POST.get("reliability") or 90),
            punctuality_score=int(request.POST.get("punctuality") or 90),
            weekly_hours_cap=int(request.POST.get("weekly_hours_cap") or cfg.max_weekly_hours),
            pay_rate=request.POST.get("pay_rate") or cfg.default_pay_rate,
            home_latitude=_CITY[0] + _random.uniform(-0.05, 0.05),
            home_longitude=_CITY[1] + _random.uniform(-0.05, 0.05), active=True)
        cg.skills.set(request.POST.getlist("skills"))

        # Optional login account for the caregiver (so they can use the app)
        email = request.POST.get("email", "").strip()
        pwd = request.POST.get("password", "").strip()
        if email and pwd:
            username = (email.split("@")[0] or cg.code.replace(" ", "").replace("#", "")).lower()
            if not User.objects.filter(username=username).exists() and not User.objects.filter(email=email).exists():
                idn = f"ID-{_random.randint(10000, 99999)}"
                while User.objects.filter(id_number=idn).exists():
                    idn = f"ID-{_random.randint(10000, 99999)}"
                u = User.objects.create(username=username, email=email, first_name=first,
                                        last_name=last, role=Role.CAREGIVER, id_number=idn,
                                        phone=cg.phone)
                u.set_password(pwd)
                u.save()
                try:
                    from allauth.account.models import EmailAddress
                    EmailAddress.objects.get_or_create(user=u, email=email,
                                                        defaults={"verified": True, "primary": True})
                except Exception:
                    pass
                cg.user = u
                cg.save(update_fields=["user"])
                messages.success(request, f"Soignant {cg.code} créé avec un accès (ID : {idn}).")
            else:
                messages.warning(request, f"Soignant {cg.code} créé, mais l'e-mail/identifiant existe déjà (pas de compte).")
        else:
            messages.success(request, f"Soignant créé : {cg.code} — {cg.full_name}.")
        log(request.user, "A ajouté un soignant", cg.code)
        return redirect("dashboard:caregiver_360", pk=cg.id)
    return render(request, "dashboard/caregiver_new.html",
                  {"cfg": cfg, "skills": Skill.objects.all()})


# ============================================================================
#  User management — manager/admin create users & grant access
# ============================================================================
@login_required
def users_list(request):
    from accounts.models import User, Role
    if not request.user.can_admin:
        messages.info(request, "Réservé au manager / administrateur.")
        return redirect("dashboard:home")
    if request.method == "POST":
        action = request.POST.get("action", "role")
        u = User.objects.filter(pk=request.POST.get("user_id")).first()
        if action == "reset_password" and u:
            new_pwd = request.POST.get("new_password", "").strip()
            if len(new_pwd) < 8:
                messages.error(request, "Le mot de passe doit contenir au moins 8 caractères.")
            else:
                u.set_password(new_pwd)
                u.save()
                log(request.user, "A réinitialisé un mot de passe", u.username)
                messages.success(request, f"Mot de passe de {u.username} réinitialisé.")
            return redirect(request.META.get("HTTP_REFERER") or "dashboard:users")
        if action == "toggle_active" and u and u != request.user:
            u.is_active = not u.is_active
            u.save(update_fields=["is_active"])
            log(request.user, "A activé/désactivé un compte", u.username)
            messages.success(request, f"Compte de {u.username} {'activé' if u.is_active else 'désactivé'}.")
            return redirect(request.META.get("HTTP_REFERER") or "dashboard:users")
        # change a user's role (grant/revoke access)
        new_role = request.POST.get("role")
        if u and new_role in dict(Role.choices):
            u.role = new_role
            u.is_staff = new_role in (Role.MANAGER, Role.ADMIN)
            u.save(update_fields=["role", "is_staff"])
            log(request.user, "A modifié le rôle d'un utilisateur", f"{u.username} → {new_role}")
            messages.success(request, f"Accès de {u.username} mis à jour : {u.get_role_display()}.")
        return redirect(request.META.get("HTTP_REFERER") or "dashboard:users")

    q = request.GET.get("q", "").strip()
    users = User.objects.all().order_by("role", "username")
    if q:
        users = users.filter(Q(username__icontains=q) | Q(first_name__icontains=q) |
                             Q(last_name__icontains=q) | Q(email__icontains=q) |
                             Q(id_number__icontains=q))
    return render(request, "dashboard/users.html", {
        "users": users, "roles": Role.choices, "q": q,
        "n_total": User.objects.count(),
    })


@login_required
def user_new(request):
    from accounts.models import User, Role
    if not request.user.can_admin:
        messages.info(request, "Réservé au manager / administrateur.")
        return redirect("dashboard:home")
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        username = request.POST.get("username", "").strip() or (email.split("@")[0] if email else "")
        pwd = request.POST.get("password", "").strip()
        role = request.POST.get("role", "COORDINATOR")
        if not username or not pwd or role not in dict(Role.choices):
            messages.error(request, "Nom d'utilisateur, mot de passe et rôle requis.")
            return redirect("dashboard:user_new")
        if User.objects.filter(username=username).exists() or (email and User.objects.filter(email=email).exists()):
            messages.error(request, "Ce nom d'utilisateur ou e-mail existe déjà.")
            return redirect("dashboard:user_new")
        idn = f"ID-{_random.randint(10000, 99999)}"
        while User.objects.filter(id_number=idn).exists():
            idn = f"ID-{_random.randint(10000, 99999)}"
        u = User.objects.create(
            username=username, email=email or f"{username}@panthergroup.cd",
            first_name=request.POST.get("first_name", "").strip(),
            last_name=request.POST.get("last_name", "").strip(),
            phone=request.POST.get("phone", "").strip(),
            role=role, id_number=idn, is_staff=role in (Role.MANAGER, Role.ADMIN))
        u.set_password(pwd)
        u.save()
        try:
            from allauth.account.models import EmailAddress
            EmailAddress.objects.get_or_create(user=u, email=u.email,
                                               defaults={"verified": True, "primary": True})
        except Exception:
            pass
        log(request.user, "A créé un utilisateur", f"{username} ({role})")
        messages.success(request, f"Utilisateur créé : {username} · {u.get_role_display()} · {idn}.")
        return redirect("dashboard:users")
    return render(request, "dashboard/user_new.html", {"roles": Role.choices})


# ============================================================================
#  Single-invoice creation (choose a client) + printable invoice
# ============================================================================
def _finance_ok(request):
    return getattr(request.user, "can_finance", False) or getattr(request.user, "is_full_access", False) or request.user.is_staff


@login_required
def invoice_new(request):
    from datetime import datetime
    from decimal import Decimal
    from clients.models import Client, Invoice
    from accounts.models import AgencySettings
    if not _finance_ok(request):
        messages.info(request, "Réservé au bureau / financier.")
        return redirect("dashboard:home")
    cfg = AgencySettings.get()

    if request.method == "POST":
        client = Client.objects.filter(pk=request.POST.get("client")).first()
        if not client:
            messages.error(request, "Choisissez un client.")
            return redirect("dashboard:invoice_new")
        period_val = request.POST.get("period", "")  # YYYY-MM
        try:
            year, month = map(int, period_val.split("-"))
            m_start = timezone.make_aware(datetime(year, month, 1))
            m_end = timezone.make_aware(datetime(year + (month == 12), (month % 12) + 1, 1))
            label = m_start.strftime("%B %Y").capitalize()
        except (ValueError, TypeError):
            label = period_val or timezone.localdate().strftime("%B %Y").capitalize()
            m_start = m_end = None

        # hours: manual, else computed from the client's completed visits that month
        hours = request.POST.get("hours", "").strip()
        if hours:
            hours = float(hours.replace(",", "."))
        elif m_start:
            hours = sum((v.check_out_at - v.check_in_at).total_seconds() / 3600
                        if v.check_in_at and v.check_out_at
                        else (v.scheduled_end - v.scheduled_start).total_seconds() / 3600
                        for v in client.visits.filter(status=VisitStatus.COMPLETED,
                                                      scheduled_start__gte=m_start, scheduled_start__lt=m_end))
        else:
            hours = 0
        hours = round(hours, 1)

        amount = request.POST.get("amount", "").strip()
        amount = Decimal(amount.replace(",", ".")) if amount else (
            Decimal(str(hours)) * client.bill_rate).quantize(Decimal("0.01"))

        inv = Invoice.objects.create(
            client=client, period=label, hours=hours, amount=amount,
            status=Invoice.Status.DUE, issued_date=timezone.localdate(),
            due_date=timezone.localdate() + timezone.timedelta(days=cfg.payment_terms_days))
        log(request.user, "A créé une facture", client.code)
        messages.success(request, f"Facture créée pour {client.code} — {amount} {cfg.currency}.")
        return redirect("dashboard:invoice_print", pk=inv.id)

    months = []
    d = timezone.localdate().replace(day=1)
    for _ in range(6):
        months.append((d.strftime("%Y-%m"), d.strftime("%B %Y").capitalize()))
        d = (d - timezone.timedelta(days=1)).replace(day=1)
    return render(request, "dashboard/invoice_new.html", {
        "clients": Client.objects.filter(active=True).order_by("code"),
        "months": months, "cfg": cfg, "preselect": request.GET.get("client", ""),
    })


@login_required
def invoice_print(request, pk):
    from clients.models import Invoice
    inv = get_object_or_404(Invoice.objects.select_related("client"), pk=pk)
    fam = _family_client(request)
    if fam is not None and inv.client_id != fam.id:
        return redirect("dashboard:family_home")
    if fam is None and not _finance_ok(request):
        return redirect("dashboard:home")
    data = pdfgen.invoice_pdf(inv)
    from accounts.models import AgencySettings
    prefix = AgencySettings.get().invoice_prefix
    return _pdf_response(data, f"{prefix}-{inv.id:05d}.pdf", download="download" in request.GET)


@login_required
def payslip(request, pk):
    """Generate a staff payslip PDF for a chosen month."""
    from datetime import datetime
    from caregivers.models import Caregiver
    if not _finance_ok(request):
        return redirect("dashboard:home")
    cg = get_object_or_404(Caregiver, pk=pk)
    period = request.GET.get("period", timezone.localdate().strftime("%Y-%m"))
    try:
        year, month = map(int, period.split("-"))
        m_start = timezone.make_aware(datetime(year, month, 1))
    except (ValueError, TypeError):
        m_start = timezone.localtime().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        year, month = m_start.year, m_start.month
    m_end = timezone.make_aware(datetime(year + (month == 12), (month % 12) + 1, 1))
    label = m_start.strftime("%B %Y").capitalize()
    data = pdfgen.payslip_pdf(cg, m_start, m_end, label)
    return _pdf_response(data, f"paie-{slugify(cg.code)}-{period}.pdf", download="download" in request.GET)


@login_required
def family_preview(request, pk):
    """Office preview of a client's family portal (read-only)."""
    if not _office_only(request):
        return redirect("dashboard:home")
    client = get_object_or_404(Client, pk=pk)
    request._preview_client = client
    # Reuse the family home computation by temporarily faking the linked client
    from datetime import timedelta
    from django.db.models import Count
    from clients.models import Invoice, Message
    now = timezone.localtime()
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    todays = (client.visits.filter(scheduled_start__gte=day, scheduled_start__lt=day + timedelta(days=1))
              .exclude(status=VisitStatus.CANCELLED).select_related("caregiver").order_by("scheduled_start"))
    today_events = []
    for v in todays:
        cg = v.caregiver.full_name if v.caregiver else "Soignant"
        if v.check_out_at:
            today_events.append({"tone": "g", "time": timezone.localtime(v.check_out_at).strftime("%H:%M"), "text": f"Visite terminée — {cg}"})
        elif v.check_in_at:
            today_events.append({"tone": "b", "time": timezone.localtime(v.check_in_at).strftime("%H:%M"), "text": f"{cg} est arrivé(e) — visite en cours"})
        else:
            today_events.append({"tone": "n", "time": timezone.localtime(v.scheduled_start).strftime("%H:%M"), "text": f"Visite prévue avec {cg}"})
    upcoming = client.visits.filter(scheduled_start__gte=now).exclude(status=VisitStatus.CANCELLED).select_related("caregiver").order_by("scheduled_start")
    recent_reports = CareReport.objects.filter(visit__client=client).select_related("caregiver").order_by("-created_at")[:5]
    mood_reports = list(CareReport.objects.filter(visit__client=client, mood__isnull=False).order_by("-created_at")[:8])[::-1]
    wellbeing = {"labels": [r.created_at.strftime("%d/%m") for r in mood_reports], "moods": [r.mood * 20 for r in mood_reports]}
    avg_mood = round(sum(r.mood for r in mood_reports) / len(mood_reports) * 20) if mood_reports else None
    team = (client.visits.filter(status=VisitStatus.COMPLETED, caregiver__isnull=False)
            .values("caregiver__code", "caregiver__first_name", "caregiver__last_name").annotate(n=Count("id")).order_by("-n")[:5])
    return render(request, "dashboard/family_home.html", {
        "client": client, "next_visit": upcoming.first(), "today_events": today_events,
        "upcoming_count": upcoming.count(), "recent_reports": recent_reports,
        "wellbeing": wellbeing, "avg_mood": avg_mood, "team": team,
        "due_invoices": Invoice.objects.filter(client=client).exclude(status="PAID").count(),
        "unread_messages": Message.objects.filter(client=client, from_agency=True, read=False).count(),
        "preview": True,
    })


@login_required
def staff_directory(request):
    """Personnel — a directory of the whole team (office staff + caregivers)."""
    from accounts.models import User, Role
    from caregivers.models import Caregiver
    if not _office_only(request):
        return redirect("dashboard:home")
    q = request.GET.get("q", "").strip()
    office = User.objects.exclude(role__in=[Role.CAREGIVER, Role.FAMILY])
    caregivers = Caregiver.objects.filter(active=True)
    if q:
        office = office.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) |
                               Q(username__icontains=q) | Q(email__icontains=q))
        caregivers = caregivers.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) |
                                       Q(code__icontains=q))
    return render(request, "dashboard/staff.html", {
        "office": office.order_by("role"), "caregivers": caregivers.order_by("code"), "q": q})


@login_required
def family_directory(request):
    """Portail familial — office access to each client's family portal."""
    from clients.models import Client
    if not _office_only(request):
        return redirect("dashboard:home")
    q = request.GET.get("q", "").strip()
    clients = Client.objects.filter(active=True).select_related("family_user")
    if q:
        clients = clients.filter(Q(code__icontains=q) | Q(first_name__icontains=q) |
                                 Q(last_name__icontains=q))
    return render(request, "dashboard/family_directory.html", {"clients": clients.order_by("code"), "q": q})


@login_required
def personnel(request):
    """Personnel directory — office staff + caregivers in one place."""
    from accounts.models import User, Role
    if not _office_only(request):
        return redirect("dashboard:home")
    office = User.objects.exclude(role__in=[Role.FAMILY, Role.CAREGIVER]).order_by("role", "username")
    caregivers = Caregiver.objects.filter(active=True).select_related("user").order_by("code")
    return render(request, "dashboard/personnel.html",
                  {"office": office, "caregivers": caregivers})


@login_required
def family_portals(request):
    """Office view — browse each client's family portal."""
    if not _office_only(request):
        return redirect("dashboard:home")
    q = request.GET.get("q", "").strip()
    clients = Client.objects.filter(active=True).select_related("family_user")
    if q:
        clients = clients.filter(Q(code__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
    return render(request, "dashboard/family_portals.html", {"clients": clients.order_by("code"), "q": q})
