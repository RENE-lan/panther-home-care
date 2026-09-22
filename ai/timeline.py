"""Client 360 'Digital Twin' — an intelligent, unified timeline built on the fly
from everything that happened to a client. No new writes: it reads existing data."""
from django.utils import timezone


def client_timeline(client, limit=40):
    """Return a chronologically sorted list of events for one client."""
    from scheduling.models import Visit, VisitStatus
    from incidents.models import Incident
    from reports.models import CareReport
    from clients.models import Invoice, CareConcern, ConsentRecord
    ev = []

    def add(dt, kind, icon, title, detail="", tone="n", link=""):
        if dt is None:
            return
        ev.append({"at": dt, "kind": kind, "icon": icon, "title": title, "detail": detail, "tone": tone, "link": link})

    for v in client.visits.select_related("caregiver").order_by("-scheduled_start")[:30]:
        if v.status == VisitStatus.COMPLETED:
            add(v.check_out_at or v.scheduled_start, "visit", "check",
                "Visite réalisée", f"{v.caregiver.code if v.caregiver else ''}".strip(), "g")
        elif v.status == VisitStatus.UNCOVERED and v.scheduled_start >= timezone.now():
            add(v.scheduled_start, "visit", "calendar", "Visite non couverte",
                "Aucun soignant affecté", "r", f"/visits/{v.pk}/")
        elif v.status == VisitStatus.MISSED:
            add(v.scheduled_start, "visit", "alert", "Visite manquée", "", "r")

    for r in CareReport.objects.filter(visit__client=client).order_by("-created_at")[:12]:
        add(r.created_at, "report", "file", "Rapport de soins",
            (getattr(r, "summary", "") or "")[:80], "n", "/reports/")

    for i in Incident.objects.filter(client=client).order_by("-created_at")[:12]:
        add(i.created_at, "incident", "alert", f"Incident — {i.get_severity_display()}",
            i.title, "r" if i.severity in ("HIGH", "CRITICAL") else "o", f"/incidents/{i.pk}/")

    for c in CareConcern.objects.filter(client=client).order_by("-created_at")[:10]:
        add(c.created_at, "concern", "activity", "Suivi clinique",
            c.get_status_display() if hasattr(c, "get_status_display") else "", "o")

    for inv in Invoice.objects.filter(client=client).order_by("-issued_date")[:10]:
        tone = "g" if inv.status == "PAID" else ("o" if inv.remaining > 0 else "n")
        add(timezone.make_aware(timezone.datetime.combine(inv.issued_date, timezone.datetime.min.time()))
            if inv.issued_date else None, "invoice", "dollar",
            f"Facture {inv.period}", f"{inv.amount} $ · {inv.get_status_display()}", tone, "/billing/")

    for cr in ConsentRecord.objects.filter(client=client):
        if cr.granted_at:
            add(cr.granted_at, "consent", "shield", "Consentement accordé", cr.get_purpose_display(), "g")
        if cr.withdrawn_at:
            add(cr.withdrawn_at, "consent", "shield", "Consentement retiré", cr.get_purpose_display(), "r")

    ev.sort(key=lambda e: e["at"], reverse=True)
    return ev[:limit]
