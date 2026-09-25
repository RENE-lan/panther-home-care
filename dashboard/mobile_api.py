"""Mobile JSON API for the React Native app — token auth, one endpoint per screen.
Talks to the same models/data as the web app (single source of truth)."""
import functools
import json

from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from accounts.models import MobileToken
from scheduling.models import Visit, VisitStatus


def _auth_user(request):
    hdr = request.META.get("HTTP_AUTHORIZATION", "")
    if hdr.startswith("Token "):
        t = MobileToken.objects.filter(key=hdr[6:].strip()).select_related("user").first()
        if t and t.user.is_active:
            return t.user
    return None


def token_required(view):
    @csrf_exempt
    @functools.wraps(view)
    def wrapped(request, *a, **k):
        u = _auth_user(request)
        if not u:
            return JsonResponse({"detail": "Non authentifié"}, status=401)
        request.mu = u
        return view(request, *a, **k)
    return wrapped


def _body(request):
    try:
        return json.loads(request.body or "{}")
    except ValueError:
        return {}


@csrf_exempt
def login(request):
    d = _body(request)
    user = authenticate(request, username=(d.get("login") or "").strip(), password=d.get("password") or "")
    if not user or not user.is_active:
        return JsonResponse({"detail": "Identifiants invalides"}, status=400)
    tok = MobileToken.issue(user)
    return JsonResponse({
        "token": tok.key, "role": user.role, "role_label": user.get_role_display(),
        "name": user.get_full_name() or user.username, "id_number": user.id_number,
        "is_full_access": user.is_full_access,
    })


@token_required
def me(request):
    u = request.mu
    return JsonResponse({"name": u.get_full_name() or u.username, "role": u.role,
                         "role_label": u.get_role_display(), "id_number": u.id_number,
                         "email": u.email})


@token_required
def logout(request):
    MobileToken.objects.filter(user=request.mu).delete()
    return JsonResponse({"ok": True})


# ---- Coordinator dashboard ----
@token_required
def dashboard(request):
    from ai.services import daily_brief, coordinator_actions
    from clients.models import Client, Invoice
    from caregivers.models import Caregiver, Certification
    from incidents.models import Incident
    now = timezone.localtime()
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today = Visit.objects.filter(scheduled_start__gte=day, scheduled_start__lt=day + timezone.timedelta(days=1))
    b = daily_brief()
    kpis = {
        "clients": Client.objects.filter(active=True).count(),
        "caregivers": Caregiver.objects.filter(active=True).count(),
        "today": today.exclude(status=VisitStatus.CANCELLED).count(),
        "completed": today.filter(status=VisitStatus.COMPLETED).count(),
        "incidents": Incident.objects.exclude(status="RESOLVED").count(),
        "outstanding": round(float(sum(i.amount for i in Invoice.objects.exclude(status="PAID")))),
    }
    actions = []
    for a in coordinator_actions(6):
        if a["type"] == "replacement":
            actions.append({"type": "replacement", "title": f"{a['client'].code} — visite non couverte à {a['time']}",
                            "detail": f"{a['n_qualified']} soignant(s) qualifié(s) à moins de {a['radius']} km",
                            "visit_id": a["visit"].id,
                            "top": (a["top"]["caregiver"].code + f" ({a['top']['score']}%)") if a.get("top") else None})
        else:
            actions.append({"type": "clinical", "title": f"{a['client'].code} — {a['symptom']} × {a['count']}",
                            "detail": "Revue clinique recommandée", "client_id": a["client"].id})
    # today's visits (mini timeline) + 7-day completed trend (mini chart)
    from datetime import timedelta
    today_list = [{"time": timezone.localtime(v.scheduled_start).strftime("%H:%M"),
                   "client": v.client.code, "caregiver": v.caregiver.code if v.caregiver else None,
                   "status": v.status} for v in today.exclude(status=VisitStatus.CANCELLED)
                  .select_related("client", "caregiver").order_by("scheduled_start")[:8]]
    trend = []
    for i in range(6, -1, -1):
        d0 = day - timedelta(days=i); d1 = d0 + timedelta(days=1)
        trend.append({"d": d0.strftime("%a")[:1],
                      "n": Visit.objects.filter(status=VisitStatus.COMPLETED, scheduled_start__gte=d0, scheduled_start__lt=d1).count()})
    return JsonResponse({"kpis": kpis, "brief": b.get("summary", ""), "actions": actions,
                         "today_list": today_list, "trend": trend,
                         "greeting": request.mu.first_name or request.mu.username})


# ---- Caregiver ----
@token_required
def my_visits(request):
    cg = getattr(request.mu, "caregiver_profile", None)
    if cg is None:
        return JsonResponse({"visits": []})
    now = timezone.localtime()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    qs = (Visit.objects.filter(caregiver=cg, scheduled_start__gte=start,
                               scheduled_start__lt=start + timezone.timedelta(days=7))
          .exclude(status=VisitStatus.CANCELLED).select_related("client").order_by("scheduled_start"))
    out = [{"id": v.id, "client": v.client.first_name, "care": v.client.care_type or "Soins",
            "start": timezone.localtime(v.scheduled_start).strftime("%d/%m %H:%M"),
            "end": timezone.localtime(v.scheduled_end).strftime("%H:%M"),
            "status": v.status, "lat": v.client.latitude, "lng": v.client.longitude,
            "checked_in": v.check_in_at is not None, "checked_out": v.check_out_at is not None}
           for v in qs]
    return JsonResponse({"visits": out})


@token_required
def checkin(request, pk):
    cg = getattr(request.mu, "caregiver_profile", None)
    v = Visit.objects.filter(pk=pk, caregiver=cg).first()
    if not v:
        return JsonResponse({"detail": "Introuvable"}, status=404)
    d = _body(request)
    try:
        lat, lng = float(d.get("lat")), float(d.get("lng"))
    except (TypeError, ValueError):
        lat = lng = None
    v.check_in(lat, lng)
    return JsonResponse({"ok": True, "status": v.status})


@token_required
def checkout(request, pk):
    from reports.models import CareReport
    from ai.services import scan_report_for_risk
    cg = getattr(request.mu, "caregiver_profile", None)
    v = Visit.objects.filter(pk=pk, caregiver=cg).first()
    if not v:
        return JsonResponse({"detail": "Introuvable"}, status=404)
    d = _body(request)
    report, _ = CareReport.objects.get_or_create(visit=v, defaults={"caregiver": cg})
    report.caregiver = cg
    report.mood = int(d.get("mood", 3))
    report.notes = (d.get("notes") or "").strip()
    if d.get("signed_by"):
        report.signed_by = d["signed_by"]
        report.signed_at = timezone.now()
    report.save()
    scan_report_for_risk(report)
    v.check_out()
    return JsonResponse({"ok": True, "status": v.status})


# ---- Family ----
@token_required
def family(request):
    from datetime import timedelta
    from django.db.models import Count
    from reports.models import CareReport
    from clients.models import Invoice
    client = request.mu.linked_clients.first() if hasattr(request.mu, "linked_clients") else None
    if client is None:
        return JsonResponse({"detail": "Aucun proche associé"}, status=404)
    now = timezone.localtime()
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    events = []
    for v in (client.visits.filter(scheduled_start__gte=day, scheduled_start__lt=day + timezone.timedelta(days=1))
              .exclude(status=VisitStatus.CANCELLED).select_related("caregiver").order_by("scheduled_start")):
        cg = v.caregiver.full_name if v.caregiver else "Soignant"
        if v.check_out_at:
            events.append({"time": timezone.localtime(v.check_out_at).strftime("%H:%M"), "text": f"Visite terminée — {cg}", "tone": "g"})
        elif v.check_in_at:
            events.append({"time": timezone.localtime(v.check_in_at).strftime("%H:%M"), "text": f"{cg} est arrivé(e)", "tone": "b"})
        else:
            events.append({"time": timezone.localtime(v.scheduled_start).strftime("%H:%M"), "text": f"Visite prévue — {cg}", "tone": "n"})
    moods = [r.mood for r in CareReport.objects.filter(visit__client=client, mood__isnull=False).order_by("-created_at")[:8]]
    wellbeing = round(sum(moods) / len(moods) * 20) if moods else None
    nxt = client.visits.filter(scheduled_start__gte=now).exclude(status=VisitStatus.CANCELLED).select_related("caregiver").order_by("scheduled_start").first()
    invoices = [{"id": i.id, "number": f"INV-{i.id:05d}", "period": i.period, "amount": float(i.amount),
                 "paid": i.status == "PAID", "status": i.get_status_display()}
                for i in Invoice.objects.filter(client=client)[:12]]
    outstanding = sum(float(i["amount"]) for i in invoices if not i["paid"])
    # last completed visit
    last = (client.visits.filter(status=VisitStatus.COMPLETED).select_related("caregiver")
            .order_by("-scheduled_start").first())
    last_visit = None
    if last:
        last_visit = {"when": timezone.localtime(last.scheduled_start).strftime("%A %d %H:%M"),
                      "caregiver": last.caregiver.full_name if last.caregiver else "Soignant"}
    # loved one status
    open_inc = client.incidents.exclude(status="RESOLVED").count() if hasattr(client, "incidents") else 0
    status = "urgent" if open_inc else ("attention" if (wellbeing is not None and wellbeing < 55) else "stable")
    status_label = {"urgent": "Attention requise", "attention": "À surveiller", "stable": "Soins en cours"}[status]
    # care plan tasks
    plan = getattr(client, "care_plan", None)
    care_plan = [t.label for t in plan.tasks.all()] if plan and hasattr(plan, "tasks") else [
        "Soins personnels", "Préparation des repas", "Mobilité", "Rappel de médicaments"]
    # today care-status flags
    todayset = list(client.visits.filter(scheduled_start__gte=day, scheduled_start__lt=day + timedelta(days=1)))
    care_status = {
        "visit_confirmed": any(v.status != VisitStatus.UNCOVERED for v in todayset),
        "care_done": any(v.status == VisitStatus.COMPLETED for v in todayset),
        "report_available": CareReport.objects.filter(visit__in=todayset).exists(),
    }
    nxt_obj = ({"when": timezone.localtime(nxt.scheduled_start).strftime("%A %d %H:%M"),
                "caregiver": nxt.caregiver.full_name if nxt.caregiver else "En affectation"} if nxt else None)
    return JsonResponse({
        "client": client.first_name,
        "loved_one": {"name": client.full_name, "status": status, "status_label": status_label,
                      "care_type": client.care_type or "Soins à domicile",
                      "next_visit": nxt_obj, "last_visit": last_visit, "care_plan": care_plan},
        "wellbeing": wellbeing, "today": events, "next": nxt_obj, "last_visit": last_visit,
        "care_status": care_status, "care_plan": care_plan,
        "invoices": invoices, "outstanding": round(outstanding),
        "insight": "Aucun problème urgent signalé." if not open_inc else f"{open_inc} incident(s) en cours — suivi par l'agence.",
    })


@token_required
def copilot(request):
    """Reuse the web copilot logic for the mobile assistant."""
    from dashboard.views import copilot_ask
    request.user = request.mu
    return copilot_ask(request)


# ============================================================================
#  Caregiver — open shifts, requests, timesheet
# ============================================================================
@token_required
def open_visits(request):
    from ai.services import open_visits_for
    cg = getattr(request.mu, "caregiver_profile", None)
    if cg is None:
        return JsonResponse({"visits": []})
    rows = open_visits_for(cg, days=45)[:30]
    pending = set(cg.visit_requests.filter(status="PENDING").values_list("visit_id", flat=True))
    out = [{"id": r["visit"].id, "client": r["visit"].client.first_name,
            "care": r["visit"].client.care_type or "Soins",
            "when": timezone.localtime(r["visit"].scheduled_start).strftime("%d/%m %H:%M"),
            "km": round(r["distance_km"], 1) if r["distance_km"] is not None else None,
            "score": r["score"], "reasons": r["reasons"],
            "why": ([("Disponible")] +
                    ([f"À proximité ({round(r['distance_km'],1)} km)"] if r["distance_km"] is not None and r["distance_km"] <= 12 else []) +
                    (["Compétences requises couvertes"] if not r["reasons"] else []) +
                    (["Pas d'heures supplémentaires", "Expérience de soins similaire"] if r["score"] >= 80 else [])),
            "pending": r["visit"].id in pending} for r in rows]
    return JsonResponse({"visits": out})


@token_required
def request_visit(request, pk):
    from ai.services import caregiver_visit_score
    from scheduling.models import VisitRequest
    cg = getattr(request.mu, "caregiver_profile", None)
    v = Visit.objects.filter(pk=pk, status=VisitStatus.UNCOVERED).first()
    if not (cg and v):
        return JsonResponse({"detail": "Introuvable"}, status=404)
    VisitRequest.objects.get_or_create(visit=v, caregiver=cg,
                                       defaults={"score": caregiver_visit_score(cg, v)["score"]})
    return JsonResponse({"ok": True})


@token_required
def my_requests(request):
    cg = getattr(request.mu, "caregiver_profile", None)
    if cg is None:
        return JsonResponse({"requests": []})
    out = [{"client": r.visit.client.first_name,
            "when": timezone.localtime(r.visit.scheduled_start).strftime("%d/%m %H:%M"),
            "score": r.score, "status": r.status} for r in cg.visit_requests.select_related("visit__client")[:30]]
    return JsonResponse({"requests": out})


@token_required
def timesheet(request):
    cg = getattr(request.mu, "caregiver_profile", None)
    if cg is None:
        return JsonResponse({"weeks": [], "total": 0})
    now = timezone.localtime()
    weeks, total = [], 0.0
    for w in range(4):
        ws = (now - timezone.timedelta(days=now.weekday() + 7 * w)).replace(hour=0, minute=0, second=0, microsecond=0)
        we = ws + timezone.timedelta(days=7)
        h = sum((v.check_out_at - v.check_in_at).total_seconds() / 3600
                for v in cg.visits.filter(status=VisitStatus.COMPLETED, scheduled_start__gte=ws, scheduled_start__lt=we)
                if v.check_in_at and v.check_out_at)
        weeks.append({"label": ws.strftime("Sem. %d/%m"), "hours": round(h, 1)})
        if w == 0:
            total = round(h, 1)
    return JsonResponse({"weeks": weeks, "week_total": total})


# ============================================================================
#  Coordinator — requests, clients, caregivers, assignment
# ============================================================================
@token_required
def requests_list(request):
    from scheduling.models import VisitRequest
    if not request.mu.is_office:
        return JsonResponse({"requests": []})
    out = [{"id": r.id, "caregiver": r.caregiver.code, "client": r.visit.client.code,
            "when": timezone.localtime(r.visit.scheduled_start).strftime("%d/%m %H:%M"), "score": r.score}
           for r in VisitRequest.objects.filter(status="PENDING").select_related("visit__client", "caregiver")[:40]]
    return JsonResponse({"requests": out})


@token_required
def decide_request(request, pk):
    from scheduling.models import VisitRequest, RequestStatus
    if not request.mu.is_office:
        return JsonResponse({"detail": "Interdit"}, status=403)
    r = VisitRequest.objects.filter(pk=pk).select_related("visit", "caregiver").first()
    if not r:
        return JsonResponse({"detail": "Introuvable"}, status=404)
    decision = _body(request).get("decision")
    if decision == "approve":
        v = r.visit
        v.caregiver = r.caregiver
        v.status = VisitStatus.SCHEDULED
        v.save(update_fields=["caregiver", "status"])
        r.status = RequestStatus.APPROVED
        r.decided_at = timezone.now(); r.save()
        v.requests.filter(status=RequestStatus.PENDING).exclude(pk=r.pk).update(status=RequestStatus.DENIED, decided_at=timezone.now())
    else:
        r.status = RequestStatus.DENIED
        r.decided_at = timezone.now(); r.save()
    return JsonResponse({"ok": True})


@token_required
def clients(request):
    from clients.models import Client, Invoice
    if not request.mu.is_office:
        return JsonResponse({"clients": []})
    q = (request.GET.get("q") or "").strip()
    qs = Client.objects.filter(active=True).prefetch_related("invoices")
    if q:
        from django.db.models import Q
        qs = qs.filter(Q(code__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
    out = []
    for c in qs.order_by("code")[:100]:
        invs = list(c.invoices.all())
        pay = "none" if not invs else ("unpaid" if any(i.status != "PAID" for i in invs) else "paid")
        out.append({"id": c.id, "code": c.code, "name": c.full_name,
                    "care": c.care_type or "—", "risk": c.risk_level, "pay": pay,
                    "family_code": c.family_code, "has_family": c.family_user_id is not None})
    return JsonResponse({"clients": out})


@token_required
def caregivers(request):
    from caregivers.models import Caregiver
    if not request.mu.is_office:
        return JsonResponse({"caregivers": []})
    out = [{"id": c.id, "code": c.code, "name": c.full_name,
            "reliability": c.reliability_score, "punctuality": c.punctuality_score}
           for c in Caregiver.objects.filter(active=True).order_by("code")[:100]]
    return JsonResponse({"caregivers": out})


@token_required
def visit_matches(request, pk):
    from ai.services import carematch_ranked
    if not request.mu.is_office:
        return JsonResponse({"matches": []})
    v = Visit.objects.filter(pk=pk).select_related("client").first()
    if not v:
        return JsonResponse({"detail": "Introuvable"}, status=404)
    rows = carematch_ranked(v, top_n=6)
    out = [{"caregiver_id": r["caregiver"].id, "code": r["caregiver"].code, "score": r["score"],
            "verdict": r["verdict"], "continuity": r["continuity_visits"],
            "km": round(r["distance_km"], 1) if r["distance_km"] is not None else None,
            "arrival": r["arrival"]["confidence"]} for r in rows]
    return JsonResponse({"client": v.client.code, "matches": out})


@token_required
def assign_visit(request, pk):
    if not request.mu.is_office:
        return JsonResponse({"detail": "Interdit"}, status=403)
    from caregivers.models import Caregiver
    v = Visit.objects.filter(pk=pk).first()
    cg = Caregiver.objects.filter(pk=_body(request).get("caregiver_id")).first()
    if not (v and cg):
        return JsonResponse({"detail": "Introuvable"}, status=404)
    v.caregiver = cg
    v.status = VisitStatus.SCHEDULED
    v.save(update_fields=["caregiver", "status"])
    return JsonResponse({"ok": True})


# ============================================================================
#  Family — messages, reports, pay
# ============================================================================
@token_required
def messages(request):
    from clients.models import Message
    client = request.mu.linked_clients.first() if hasattr(request.mu, "linked_clients") else None
    if request.method == "POST":
        if client is None:
            return JsonResponse({"detail": "Liez d'abord votre proche pour écrire à l'agence."}, status=400)
        body = (_body(request).get("body") or "").strip()
        if body:
            Message.objects.create(client=client, sender=request.mu, from_agency=False, body=body)
        return JsonResponse({"ok": True})
    if client is None:
        return JsonResponse({"messages": [], "linked": False})
    thread = client.messages.all()
    thread.filter(from_agency=True, read=False).update(read=True)
    out = [{"from_agency": m.from_agency, "body": m.body,
            "at": timezone.localtime(m.created_at).strftime("%d/%m %H:%M")} for m in thread]
    return JsonResponse({"messages": out, "linked": True})


@token_required
def reports(request):
    from reports.models import CareReport
    client = request.mu.linked_clients.first() if hasattr(request.mu, "linked_clients") else None
    if client is None:
        return JsonResponse({"reports": [], "linked": False})
    out = []
    for r in CareReport.objects.filter(visit__client=client).select_related("caregiver", "visit").order_by("-created_at")[:30]:
        v = r.visit
        out.append({
            "id": r.id, "date": timezone.localtime(r.created_at).strftime("%d %b %Y"),
            "iso": timezone.localtime(r.created_at).strftime("%Y-%m-%d"),
            "time": timezone.localtime(r.created_at).strftime("%H:%M"),
            "caregiver": r.caregiver.full_name if r.caregiver else "Soignant",
            "mood": r.get_mood_display(), "notes": r.notes, "signed": bool(r.signed_by),
            "arrival": timezone.localtime(v.check_in_at).strftime("%H:%M") if v.check_in_at else None,
            "departure": timezone.localtime(v.check_out_at).strftime("%H:%M") if v.check_out_at else None,
            "evv": "Vérifié" if v.check_in_at else "En attente",
            "tasks": list(r.tasks_completed) if getattr(r, "tasks_completed", None) else [],
        })
    return JsonResponse({"reports": out, "linked": True})


@token_required
def pay_invoice(request, pk):
    from clients.models import Invoice
    client = request.mu.linked_clients.first() if hasattr(request.mu, "linked_clients") else None
    inv = Invoice.objects.filter(pk=pk, client=client).first() if client else None
    if not inv:
        return JsonResponse({"detail": "Introuvable"}, status=404)
    inv.apply_payment(inv.remaining)
    return JsonResponse({"ok": True})


@token_required
def schedule(request):
    """Coordinator week calendar — visits grouped by day, with coverage gaps."""
    from datetime import timedelta
    if not request.mu.is_office:
        return JsonResponse({"days": []})
    try:
        offset = int(request.GET.get("week", 0))
    except ValueError:
        offset = 0
    now = timezone.localtime()
    monday = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(weeks=offset)
    days = []
    for i in range(7):
        d0 = monday + timedelta(days=i)
        d1 = d0 + timedelta(days=1)
        vs = (Visit.objects.filter(scheduled_start__gte=d0, scheduled_start__lt=d1)
              .exclude(status=VisitStatus.CANCELLED).select_related("client", "caregiver").order_by("scheduled_start"))
        visits = [{"id": v.id, "client": v.client.code, "name": v.client.first_name,
                   "time": timezone.localtime(v.scheduled_start).strftime("%H:%M"),
                   "end": timezone.localtime(v.scheduled_end).strftime("%H:%M"),
                   "caregiver": v.caregiver.code if v.caregiver else None,
                   "status": v.status} for v in vs]
        days.append({"label": ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"][i],
                     "date": d0.strftime("%d/%m"), "is_today": d0.date() == now.date(),
                     "visits": visits,
                     "uncovered": sum(1 for x in visits if x["status"] == "UNCOVERED")})
    return JsonResponse({
        "week_label": f"{monday.strftime('%d/%m')} – {(monday + timedelta(days=6)).strftime('%d/%m')}",
        "offset": offset, "days": days,
        "total": sum(len(d["visits"]) for d in days),
        "uncovered": sum(d["uncovered"] for d in days),
    })


@csrf_exempt
def signup(request):
    """Self-service account creation from the app (family or caregiver)."""
    import secrets
    from accounts.models import User, Role
    d = _body(request)
    name = (d.get("name") or "").strip()
    email = (d.get("email") or "").strip().lower()
    pwd = d.get("password") or ""
    phone = (d.get("phone") or "").strip()
    role = d.get("role") if d.get("role") in (Role.FAMILY, Role.CAREGIVER) else Role.FAMILY
    if not name or not email or len(pwd) < 8:
        return JsonResponse({"detail": "Nom, e-mail et mot de passe (8+ caractères) requis."}, status=400)
    username = email.split("@")[0]
    base = username
    i = 1
    while User.objects.filter(username=username).exists():
        username = f"{base}{i}"; i += 1
    if User.objects.filter(email=email).exists():
        return JsonResponse({"detail": "Cet e-mail a déjà un compte."}, status=400)
    parts = name.split(" ", 1)
    idn = f"ID-{secrets.randbelow(90000) + 10000}"
    while User.objects.filter(id_number=idn).exists():
        idn = f"ID-{secrets.randbelow(90000) + 10000}"
    user = User.objects.create(username=username, email=email, first_name=parts[0],
                               last_name=parts[1] if len(parts) > 1 else "", phone=phone,
                               role=role, id_number=idn)
    user.set_password(pwd)
    user.save()
    try:
        from allauth.account.models import EmailAddress
        EmailAddress.objects.get_or_create(user=user, email=email, defaults={"verified": True, "primary": True})
    except Exception:
        pass
    if role == Role.CAREGIVER:
        from caregivers.models import Caregiver
        nums = [int("".join(ch for ch in c if ch.isdigit()) or 0) for c in Caregiver.objects.values_list("code", flat=True)]
        code = f"Soignant #{(max(nums) + 1) if nums else 1:03d}"
        Caregiver.objects.create(code=code, first_name=parts[0], last_name=parts[1] if len(parts) > 1 else "",
                                 phone=phone, user=user, active=True)
    tok = MobileToken.issue(user)
    return JsonResponse({"token": tok.key, "role": user.role, "role_label": user.get_role_display(),
                         "name": user.get_full_name() or user.username, "id_number": user.id_number,
                         "is_full_access": user.is_full_access})


# ============================================================================
#  Caregiver home dashboard + visit detail + incident (mockup flow)
# ============================================================================
@token_required
def cg_home(request):
    from datetime import timedelta
    from ai.services import haversine_km
    cg = getattr(request.mu, "caregiver_profile", None)
    if cg is None:
        return JsonResponse({"caregiver": False})
    now = timezone.localtime()
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today = list(cg.visits.filter(scheduled_start__gte=day, scheduled_start__lt=day + timedelta(days=1))
                 .exclude(status=VisitStatus.CANCELLED).select_related("client").order_by("scheduled_start"))
    counts = {"total": len(today),
              "completed": sum(1 for v in today if v.status == VisitStatus.COMPLETED),
              "in_progress": sum(1 for v in today if v.status == VisitStatus.IN_PROGRESS),
              "upcoming": sum(1 for v in today if v.status in (VisitStatus.SCHEDULED, VisitStatus.UNCOVERED))}
    nxt = next((v for v in today if v.status in (VisitStatus.SCHEDULED, VisitStatus.IN_PROGRESS)), None) \
        or cg.visits.filter(scheduled_start__gte=now).exclude(status=VisitStatus.CANCELLED).select_related("client").order_by("scheduled_start").first()
    next_visit = None
    if nxt:
        km = None
        try:
            if cg.home_latitude and nxt.client.latitude:
                km = round(haversine_km(cg.home_latitude, cg.home_longitude, nxt.client.latitude, nxt.client.longitude), 1)
        except Exception:
            km = None
        next_visit = {"id": nxt.id, "client": nxt.client.code, "name": nxt.client.first_name,
                      "care": nxt.client.care_type or "Soins à domicile",
                      "time": timezone.localtime(nxt.scheduled_start).strftime("%H:%M"),
                      "end": timezone.localtime(nxt.scheduled_end).strftime("%H:%M"), "km": km,
                      "status": nxt.status}
    # certification warning + AI tips
    cert_warn = None
    soonest = cg.certifications.filter(expires_on__gte=timezone.localdate()).order_by("expires_on").first()
    if soonest and (soonest.expires_on - timezone.localdate()).days <= 45:
        cert_warn = {"name": soonest.name, "days": (soonest.expires_on - timezone.localdate()).days}
    tips = []
    if next_visit:
        tips.append(f"Vous avez une visite à {next_visit['time']} ({next_visit['client']}).")
    if cert_warn:
        tips.append(f"Votre certification « {cert_warn['name']} » expire dans {cert_warn['days']} jours.")
    # today's care score
    late_thresh = 0
    try:
        from accounts.models import AgencySettings
        late_thresh = AgencySettings.get().late_threshold_min
    except Exception:
        pass
    late_risk = sum(1 for v in today if v.status in (VisitStatus.SCHEDULED,) and v.scheduled_start < now)
    times = sorted((v.scheduled_start, v.scheduled_end) for v in today)
    conflicts = sum(1 for i in range(1, len(times)) if times[i][0] < times[i-1][1])
    alerts_n = (1 if cert_warn else 0) + late_risk + conflicts
    care_score = {"visits": counts["total"], "conflicts": conflicts, "late_risks": late_risk, "alerts": alerts_n}
    # dynamic AI assistant
    assistant = {"type": "ready", "title": "Votre journée est prête", "lines": [
        f"{counts['total']} visite(s)", f"{conflicts} conflit(s)", f"{late_risk} retard(s) prévu(s)"]}
    if next_visit and next_visit.get("status") == "IN_PROGRESS":
        assistant = {"type": "active", "title": "Visite en cours",
                     "lines": [f"{next_visit['client']} — soins en cours"], "visit_id": next_visit["id"]}
    elif nxt and nxt.status == VisitStatus.SCHEDULED:
        mins = int((nxt.scheduled_start - now).total_seconds() // 60)
        km = next_visit.get("km") if next_visit else None
        travel = round(km * 2) if km else None
        if 0 <= mins <= 90:
            lines = [f"Votre prochaine visite commence dans {mins} min."]
            if travel:
                lines.append(f"Trajet estimé à {travel} min.")
            assistant = {"type": "soon", "title": "Attention", "lines": lines, "visit_id": next_visit["id"]}
    return JsonResponse({"caregiver": True, "name": request.mu.first_name or request.mu.username,
                         "today": counts, "next_visit": next_visit, "cert_warning": cert_warn,
                         "tips": tips, "care_score": care_score, "assistant": assistant})


@token_required
def visit_detail(request, pk):
    cg = getattr(request.mu, "caregiver_profile", None)
    v = Visit.objects.filter(pk=pk).select_related("client", "caregiver").first()
    if not v:
        return JsonResponse({"detail": "Introuvable"}, status=404)
    plan = getattr(v.client, "care_plan", None)
    tasks = [{"label": t.label} for t in plan.tasks.all()] if plan and hasattr(plan, "tasks") else [
        {"label": "Rappel de médicaments"}, {"label": "Préparation des repas"},
        {"label": "Soins personnels"}, {"label": "Assistance mobilité"}]
    return JsonResponse({
        "id": v.id, "client": v.client.code, "name": v.client.full_name,
        "care": v.client.care_type or "Soins à domicile",
        "address": v.client.address or "Résidence du client",
        "time": timezone.localtime(v.scheduled_start).strftime("%H:%M"),
        "end": timezone.localtime(v.scheduled_end).strftime("%H:%M"),
        "status": v.status, "checked_in": v.check_in_at is not None,
        "lat": v.client.latitude, "lng": v.client.longitude,
        "note": (plan.summary if plan and getattr(plan, "summary", "") else "Suivez le plan de soins actuel et signalez tout changement."),
        "tasks": tasks,
        "important": ("Précautions risque de chute" if getattr(v.client, "risk_level", "") in ("HIGH", "MEDIUM") else ""),
        "contact_family": (v.client.family_user.get_full_name() if getattr(v.client, "family_user", None) else None),
        "contact_coordinator": __import__("accounts.models", fromlist=["AgencySettings"]).AgencySettings.get().agency_name,
    })


@token_required
def report_incident(request, pk):
    from incidents.models import Incident
    cg = getattr(request.mu, "caregiver_profile", None)
    v = Visit.objects.filter(pk=pk).select_related("client").first()
    if not v:
        return JsonResponse({"detail": "Introuvable"}, status=404)
    d = _body(request)
    sev = {"low": "LOW", "medium": "MEDIUM", "high": "CRITICAL"}.get(d.get("severity"), "MEDIUM")
    desc = (d.get("description") or "").strip()
    photo = d.get("photo")
    if photo:
        import base64, os
        from django.conf import settings as dj
        try:
            folder = os.path.join(dj.MEDIA_ROOT, "incidents")
            os.makedirs(folder, exist_ok=True)
            fname = f"inc_{timezone.now().strftime('%Y%m%d%H%M%S')}_{v.client.code.split('#')[-1]}.jpg"
            with open(os.path.join(folder, fname), "wb") as f:
                f.write(base64.b64decode(photo))
            desc = (desc + f"\n[Photo: {dj.MEDIA_URL}incidents/{fname}]").strip()
        except Exception:
            pass
    Incident.objects.create(
        title=d.get("type", "Incident") + f" — {v.client.code}", client=v.client, caregiver=cg,
        severity=sev, description=desc, status="OPEN")
    return JsonResponse({"ok": True})


# ---- Coordinator: personnel + family portals (mobile) ----
@token_required
def personnel(request):
    from accounts.models import User, Role
    from caregivers.models import Caregiver
    if not request.mu.is_office:
        return JsonResponse({"office": [], "caregivers": []})
    office = [{"name": u.get_full_name() or u.username, "role": u.get_role_display(), "id": u.id_number}
              for u in User.objects.exclude(role__in=[Role.FAMILY, Role.CAREGIVER]).order_by("role")[:60]]
    cgs = [{"code": c.code, "name": c.full_name, "reliability": c.reliability_score, "has_account": c.user_id is not None}
           for c in Caregiver.objects.filter(active=True).order_by("code")[:100]]
    return JsonResponse({"office": office, "caregivers": cgs})


@token_required
def family_portals(request):
    from clients.models import Client
    if not request.mu.is_office:
        return JsonResponse({"clients": []})
    out = [{"id": c.id, "code": c.code, "name": c.full_name,
            "has_family": c.family_user_id is not None}
           for c in Client.objects.filter(active=True).select_related("family_user").order_by("code")[:100]]
    return JsonResponse({"clients": out})


# ============================================================================
#  Mobile admin — manager/admin manages users (passwords, roles, accounts)
# ============================================================================
@token_required
def roles(request):
    from accounts.models import Role
    return JsonResponse({"roles": [{"value": v, "label": l} for v, l in Role.choices]})


@token_required
def admin_users(request):
    from accounts.models import User
    from django.db.models import Q
    if not request.mu.can_admin:
        return JsonResponse({"detail": "Réservé au manager/admin."}, status=403)
    q = (request.GET.get("q") or "").strip()
    qs = User.objects.all().order_by("role", "username")
    if q:
        qs = qs.filter(Q(username__icontains=q) | Q(first_name__icontains=q) |
                       Q(last_name__icontains=q) | Q(email__icontains=q) | Q(id_number__icontains=q))
    out = [{"id": u.id, "name": u.get_full_name() or u.username, "username": u.username,
            "email": u.email, "id_number": u.id_number, "role": u.role,
            "role_label": u.get_role_display(), "active": u.is_active, "self": u.id == request.mu.id}
           for u in qs[:100]]
    return JsonResponse({"users": out})


@token_required
def admin_reset_password(request, pk):
    from accounts.models import User
    if not request.mu.can_admin:
        return JsonResponse({"detail": "Interdit"}, status=403)
    u = User.objects.filter(pk=pk).first()
    pwd = (_body(request).get("password") or "").strip()
    if not u or len(pwd) < 8:
        return JsonResponse({"detail": "Mot de passe de 8+ caractères requis."}, status=400)
    u.set_password(pwd); u.save()
    return JsonResponse({"ok": True})


@token_required
def admin_set_role(request, pk):
    from accounts.models import User, Role
    if not request.mu.can_admin:
        return JsonResponse({"detail": "Interdit"}, status=403)
    u = User.objects.filter(pk=pk).first()
    role = _body(request).get("role")
    if not u or role not in dict(Role.choices) or u.id == request.mu.id:
        return JsonResponse({"detail": "Impossible."}, status=400)
    u.role = role
    u.is_staff = role in (Role.MANAGER, Role.ADMIN)
    u.save(update_fields=["role", "is_staff"])
    return JsonResponse({"ok": True, "role_label": u.get_role_display()})


@token_required
def admin_toggle_active(request, pk):
    from accounts.models import User
    if not request.mu.can_admin:
        return JsonResponse({"detail": "Interdit"}, status=403)
    u = User.objects.filter(pk=pk).first()
    if not u or u.id == request.mu.id:
        return JsonResponse({"detail": "Impossible."}, status=400)
    u.is_active = not u.is_active
    u.save(update_fields=["is_active"])
    return JsonResponse({"ok": True, "active": u.is_active})


@token_required
def admin_create_user(request):
    import secrets
    from accounts.models import User, Role
    if not request.mu.can_admin:
        return JsonResponse({"detail": "Interdit"}, status=403)
    d = _body(request)
    name = (d.get("name") or "").strip()
    email = (d.get("email") or "").strip().lower()
    pwd = d.get("password") or ""
    role = d.get("role") if d.get("role") in dict(Role.choices) else Role.COORDINATOR
    if not name or len(pwd) < 8:
        return JsonResponse({"detail": "Nom et mot de passe (8+) requis."}, status=400)
    username = (email.split("@")[0] if email else name.lower().replace(" ", ""))
    base = username or "user"; username = base; i = 1
    while User.objects.filter(username=username).exists():
        username = f"{base}{i}"; i += 1
    if email and User.objects.filter(email=email).exists():
        return JsonResponse({"detail": "Cet e-mail existe déjà."}, status=400)
    parts = name.split(" ", 1)
    idn = f"ID-{secrets.randbelow(90000) + 10000}"
    while User.objects.filter(id_number=idn).exists():
        idn = f"ID-{secrets.randbelow(90000) + 10000}"
    u = User.objects.create(username=username, email=email or f"{username}@panthergroup.cd",
                            first_name=parts[0], last_name=parts[1] if len(parts) > 1 else "",
                            phone=(d.get("phone") or "").strip(), role=role, id_number=idn,
                            is_staff=role in (Role.MANAGER, Role.ADMIN))
    u.set_password(pwd); u.save()
    try:
        from allauth.account.models import EmailAddress
        EmailAddress.objects.get_or_create(user=u, email=u.email, defaults={"verified": True, "primary": True})
    except Exception:
        pass
    if role == Role.CAREGIVER:
        from caregivers.models import Caregiver
        nums = [int("".join(ch for ch in c if ch.isdigit()) or 0) for c in Caregiver.objects.values_list("code", flat=True)]
        Caregiver.objects.create(code=f"Soignant #{(max(nums) + 1) if nums else 1:03d}",
                                 first_name=parts[0], last_name=parts[1] if len(parts) > 1 else "", user=u, active=True)
    return JsonResponse({"ok": True, "username": username, "id_number": idn, "role_label": u.get_role_display()})


@token_required
def push_token(request):
    tok = (_body(request).get("token") or "").strip()
    if tok:
        request.mu.push_token = tok[:200]
        request.mu.save(update_fields=["push_token"])
    return JsonResponse({"ok": True})


@token_required
def link_family(request):
    """Family self-service: link my account to a patient using the invitation code."""
    from clients.models import Client
    code = (_body(request).get("code") or "").strip().upper()
    if not code:
        return JsonResponse({"detail": "Entrez un code."}, status=400)
    client = Client.objects.filter(family_code=code).first()
    if not client:
        return JsonResponse({"detail": "Code invalide."}, status=404)
    if client.family_user_id and client.family_user_id != request.mu.id:
        return JsonResponse({"detail": "Ce proche est déjà lié à un autre compte."}, status=400)
    request.mu.role = "FAMILY"
    request.mu.save(update_fields=["role"])
    client.family_user = request.mu
    client.save(update_fields=["family_user"])
    return JsonResponse({"ok": True, "client": client.first_name})


@token_required
def admin_link_family(request):
    """Admin links a family user to a client (by client code or family code)."""
    from accounts.models import User
    from clients.models import Client
    if not request.mu.can_admin:
        return JsonResponse({"detail": "Interdit"}, status=403)
    d = _body(request)
    u = User.objects.filter(pk=d.get("user_id")).first()
    ref = (d.get("client") or "").strip()
    client = Client.objects.filter(code__iexact=ref).first() or Client.objects.filter(family_code__iexact=ref.upper()).first()
    if not (u and client):
        return JsonResponse({"detail": "Utilisateur ou client introuvable."}, status=404)
    u.role = "FAMILY"; u.save(update_fields=["role"])
    client.family_user = u; client.save(update_fields=["family_user"])
    return JsonResponse({"ok": True, "client": client.code})


# ============================================================================
#  Family — documents, team/contacts, notifications, visits
# ============================================================================
def _family_client(request):
    return request.mu.linked_clients.first() if hasattr(request.mu, "linked_clients") else None


@token_required
def family_documents(request):
    from reports.models import CareReport
    client = _family_client(request)
    if client is None:
        return JsonResponse({"documents": [], "linked": False})
    docs = []
    plan = getattr(client, "care_plan", None)
    if plan:
        docs.append({"kind": "plan", "title": "Plan de soins", "subtitle": "À jour", "id": None})
    for a in getattr(client, "assessments", []).all()[:5] if hasattr(client, "assessments") else []:
        docs.append({"kind": "assessment", "title": "Évaluation", "subtitle": a.created_at.strftime("%d %b %Y"), "id": a.id})
    for r in CareReport.objects.filter(visit__client=client).order_by("-created_at")[:10]:
        docs.append({"kind": "report", "title": "Rapport de visite", "subtitle": timezone.localtime(r.created_at).strftime("%d %b %Y"), "id": r.id})
    return JsonResponse({"documents": docs, "linked": True})


@token_required
def family_team(request):
    from django.db.models import Count
    from accounts.models import AgencySettings
    client = _family_client(request)
    if client is None:
        return JsonResponse({"team": [], "agency": None, "linked": False})
    rows = (client.visits.filter(status=VisitStatus.COMPLETED, caregiver__isnull=False)
            .values("caregiver__first_name", "caregiver__last_name", "caregiver__phone")
            .annotate(n=Count("id")).order_by("-n")[:6])
    team = [{"name": f"{r['caregiver__first_name']} {r['caregiver__last_name']}".strip(),
             "phone": r["caregiver__phone"], "visits": r["n"], "role": "Soignant"} for r in rows]
    cfg = AgencySettings.get()
    agency = {"name": cfg.agency_name, "phone": cfg.notify_sms or "", "email": cfg.notify_email or ""}
    return JsonResponse({"team": team, "agency": agency, "linked": True})


@token_required
def family_notifications(request):
    from reports.models import CareReport
    from clients.models import Invoice
    client = _family_client(request)
    if client is None:
        return JsonResponse({"notifications": [], "linked": False})
    items = []
    for v in client.visits.filter(status=VisitStatus.COMPLETED).select_related("caregiver").order_by("-scheduled_start")[:5]:
        items.append({"icon": "check", "tone": "g", "title": "Visite terminée",
                      "text": f"{v.caregiver.full_name if v.caregiver else 'Soignant'} — soins effectués",
                      "when": timezone.localtime(v.scheduled_start).strftime("%d %b %H:%M")})
    for r in CareReport.objects.filter(visit__client=client).order_by("-created_at")[:3]:
        items.append({"icon": "file", "tone": "b", "title": "Rapport disponible",
                      "text": "Un nouveau rapport de visite est disponible",
                      "when": timezone.localtime(r.created_at).strftime("%d %b %H:%M")})
    for i in Invoice.objects.filter(client=client).exclude(status="PAID")[:3]:
        items.append({"icon": "card", "tone": "a", "title": "Nouvelle facture",
                      "text": f"{i.period} — {float(i.amount):.0f} $ en attente", "when": ""})
    return JsonResponse({"notifications": items[:12], "linked": True})


@token_required
def family_visits(request):
    from datetime import timedelta
    client = _family_client(request)
    if client is None:
        return JsonResponse({"upcoming": [], "past": [], "linked": False})
    now = timezone.localtime()
    def ser(v):
        return {"id": v.id, "when": timezone.localtime(v.scheduled_start).strftime("%a %d %b · %H:%M"),
                "end": timezone.localtime(v.scheduled_end).strftime("%H:%M"),
                "caregiver": v.caregiver.full_name if v.caregiver else "En affectation",
                "status": v.status, "evv": "Vérifié" if v.check_in_at else "En attente"}
    up = [ser(v) for v in client.visits.filter(scheduled_start__gte=now).exclude(status=VisitStatus.CANCELLED).select_related("caregiver").order_by("scheduled_start")[:15]]
    past = [ser(v) for v in client.visits.filter(scheduled_start__lt=now).exclude(status=VisitStatus.CANCELLED).select_related("caregiver").order_by("-scheduled_start")[:15]]
    return JsonResponse({"upcoming": up, "past": past, "linked": True})


@token_required
def caregiver_alerts(request):
    from datetime import timedelta
    cg = getattr(request.mu, "caregiver_profile", None)
    if cg is None:
        return JsonResponse({"alerts": []})
    now = timezone.localtime()
    alerts = []
    # certification expiry
    soon = cg.certifications.filter(expires_on__gte=timezone.localdate()).order_by("expires_on").first()
    if soon:
        days = (soon.expires_on - timezone.localdate()).days
        if days <= 30:
            alerts.append({"level": "orange", "title": "Certification bientôt expirée",
                           "text": f"{soon.name} expire dans {days} jours"})
    # upcoming visit reminder (next 45 min)
    nxt = cg.visits.filter(status=VisitStatus.SCHEDULED, scheduled_start__gte=now,
                           scheduled_start__lte=now + timedelta(minutes=45)).select_related("client").first()
    if nxt:
        mins = int((nxt.scheduled_start - now).total_seconds() // 60)
        alerts.append({"level": "yellow", "title": "Visite imminente",
                       "text": f"{nxt.client.first_name} commence dans {mins} min"})
    # late clock-in risk (scheduled start passed, not checked in)
    for v in cg.visits.filter(status=VisitStatus.SCHEDULED, scheduled_start__lt=now,
                              scheduled_start__gte=now - timedelta(hours=6)).select_related("client"):
        alerts.append({"level": "red", "title": "Retard de pointage",
                       "text": f"{v.client.first_name} — visite non pointée"})
    if not alerts:
        alerts.append({"level": "blue", "title": "Tout est à jour", "text": "Aucune alerte pour le moment"})
    return JsonResponse({"alerts": alerts})


@token_required
def link_demo(request):
    """One-tap demo: link this family account to an example client that has data."""
    from clients.models import Client
    from reports.models import CareReport
    # prefer an unlinked client that already has care reports (so screens are populated)
    from clients.models import Invoice
    client = None
    cands = list(Client.objects.filter(active=True, family_user__isnull=True).order_by("code"))
    for c in cands:
        if CareReport.objects.filter(visit__client=c).exists() and Invoice.objects.filter(client=c).exists():
            client = c; break
    if client is None:
        for c in cands:
            if CareReport.objects.filter(visit__client=c).exists():
                client = c; break
    if client is None:
        client = Client.objects.filter(active=True, family_user__isnull=True).first() or Client.objects.filter(active=True).first()
    if client is None:
        return JsonResponse({"detail": "Aucun client de démonstration disponible."}, status=404)
    request.mu.role = "FAMILY"
    request.mu.save(update_fields=["role"])
    client.family_user = request.mu
    client.save(update_fields=["family_user"])
    return JsonResponse({"ok": True, "client": client.first_name})


@token_required
def caregiver_assistant(request):
    """Assistant IA soignant (mobile) — répond à tout, garde-fous cliniques."""
    from ai.caregiver_assistant import answer
    cg = getattr(request.mu, "caregiver_profile", None)
    if cg is None:
        return JsonResponse({"answer": "Assistant réservé aux soignants."}, status=200)
    body = _body(request)
    q = (body.get("question") or body.get("q") or "").strip()
    if not q:
        return JsonResponse({"detail": "Question requise."}, status=400)
    return JsonResponse(answer(cg, q, body.get("history") or []))
