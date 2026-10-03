"""Panther Attention Engine — instead of 50 notifications, it clusters the signals
that concern the SAME client and surfaces 'what needs attention', why, and a next step.
It presents signals and recommendations — never certainties, never autonomous action."""
from django.utils import timezone
from django.core.cache import cache


_WEIGHTS = {"incident": 40, "incident_high": 60, "uncovered": 30, "concern": 25,
            "no_consent": 20, "unsigned": 10, "overdue": 15}


def _collect():
    from datetime import timedelta
    from scheduling.models import Visit, VisitStatus
    from incidents.models import Incident
    from reports.models import CareReport
    from clients.models import Client, Invoice, CareConcern, ConsentRecord
    now = timezone.now()
    horizon = now + timedelta(days=7)
    recent = now - timedelta(days=30)
    sig = {}

    def add(cid, key, label, weight):
        if cid is None:
            return
        row = sig.setdefault(cid, {})
        cur = row.get(key)
        if cur:
            cur["count"] += 1
        else:
            row[key] = {"key": key, "label": label, "weight": weight, "count": 1}

    for i in Incident.objects.filter(created_at__gte=recent).exclude(status="RESOLVED"):
        high = i.severity in ("HIGH", "CRITICAL")
        add(i.client_id, "incident", f"Incident {i.get_severity_display().lower()} : {i.title}",
            _WEIGHTS["incident_high"] if high else _WEIGHTS["incident"])
    for v in Visit.objects.filter(status=VisitStatus.UNCOVERED, scheduled_start__gte=now,
                                  scheduled_start__lte=horizon):
        add(v.client_id, "uncovered", "Visite non couverte à venir", _WEIGHTS["uncovered"])
    for c in CareConcern.objects.exclude(status="RESOLVED"):
        add(c.client_id, "concern", "Suivi clinique actif", _WEIGHTS["concern"])
    consented = set(ConsentRecord.objects.filter(purpose="CARE", granted=True, withdrawn_at__isnull=True)
                    .values_list("client_id", flat=True))
    for inv in Invoice.objects.all():
        if inv.remaining > 0 and (inv.due_date or inv.issued_date) < timezone.localdate():
            add(inv.client_id, "overdue", "Facture en retard", _WEIGHTS["overdue"])
    for r in CareReport.objects.filter(signed_by="", created_at__gte=now - timedelta(days=10)).select_related("visit"):
        if r.visit_id and r.visit.client_id:
            add(r.visit.client_id, "unsigned", "Rapport non signé", _WEIGHTS["unsigned"])
    # missing consent only for clients that already have other signals (avoid noise)
    for cid in list(sig.keys()):
        if cid not in consented:
            add(cid, "no_consent", "Consentement de soins manquant", _WEIGHTS["no_consent"])
    out = {}
    for cid, keys in sig.items():
        signals = []
        score = 0
        for k, d in keys.items():
            score += d["weight"]  # count once per signal type
            lbl = d["label"] + (f" ({d['count']})" if d["count"] > 1 else "")
            signals.append({"key": k, "label": lbl})
        out[cid] = {"signals": signals, "score": score}
    return out


def _suggested_step(keys):
    if "incident" in keys and ("uncovered" in keys or "no_consent" in keys):
        return "Examiner le dossier et planifier une réunion d'équipe."
    if "incident" in keys:
        return "Examiner l'incident et confirmer le suivi."
    if "uncovered" in keys:
        return "Affecter un soignant (Auto-remplir) ou proposer un remplaçant."
    if "overdue" in keys:
        return "Relancer / encaisser la facture."
    if "concern" in keys:
        return "Revoir le suivi clinique avec le coordinateur."
    return "Examiner le dossier client."


def attention_items(limit=8):
    """Top clients needing attention (2+ signals), highest score first. Cached 60s."""
    cached = cache.get("attention_items")
    if cached is not None:
        return cached[:limit]
    from clients.models import Client
    sig = _collect()
    ids = [cid for cid, d in sig.items() if len(d["signals"]) >= 2]
    clients = {c.id: c for c in Client.objects.filter(id__in=ids)}
    rows = []
    for cid in ids:
        c = clients.get(cid)
        if not c:
            continue
        d = sig[cid]
        keys = {s["key"] for s in d["signals"]}
        rows.append({
            "client": c, "score": d["score"],
            "signals": d["signals"],
            "why": "Plusieurs événements concernent le même client.",
            "next": _suggested_step(keys),
            "level": "high" if d["score"] >= 80 else "medium",
        })
    rows.sort(key=lambda r: r["score"], reverse=True)
    cache.set("attention_items", rows, 60)
    return rows[:limit]


def attention_for_client(client):
    """Signals for one client (for the Client 360 AI Insights card)."""
    sig = _collect().get(client.id)
    if not sig or len(sig["signals"]) < 1:
        return None
    keys = {s["key"] for s in sig["signals"]}
    return {"score": sig["score"], "signals": sig["signals"],
            "next": _suggested_step(keys),
            "level": "high" if sig["score"] >= 80 else "medium"}
