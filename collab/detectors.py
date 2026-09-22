"""Home-care work detectors. The AI finds the work; the human decides.
Each returns candidate work-item dicts."""
from datetime import timedelta
from django.utils import timezone


def detect_cert_expiry():
    from caregivers.models import Certification
    today = timezone.localdate()
    horizon = today + timedelta(days=30)
    out = []
    for cert in Certification.objects.filter(expires_on__gte=today, expires_on__lte=horizon).select_related("caregiver"):
        days = (cert.expires_on - today).days
        out.append({
            "source_key": f"cert:{cert.pk}", "category": "CERT",
            "priority": "HIGH" if days <= 10 else "MEDIUM",
            "title": f"{cert.caregiver.full_name} — {cert.name} expire dans {days} j",
            "detail": f"Certification a renouveler avant le {cert.expires_on:%d/%m/%Y}.",
            "link": "/compliance/",
            "due_at": timezone.make_aware(timezone.datetime.combine(cert.expires_on, timezone.datetime.min.time())),
        })
    return out


def detect_uncovered_visits():
    from scheduling.models import Visit, VisitStatus
    now = timezone.localtime()
    horizon = now + timedelta(days=7)
    out = []
    for v in Visit.objects.filter(status=VisitStatus.UNCOVERED, scheduled_start__gte=now,
                                  scheduled_start__lte=horizon).select_related("client")[:500]:
        mins = int((v.scheduled_start - now).total_seconds() // 60)
        out.append({
            "source_key": f"uncovered:{v.pk}", "category": "UNCOVERED",
            "priority": "HIGH" if mins <= 24 * 60 else "MEDIUM",
            "title": f"{v.client.code} — visite non couverte {timezone.localtime(v.scheduled_start):%d/%m %H:%M}",
            "detail": "Aucun soignant affecte. Proposez un remplacement.",
            "link": f"/visits/{v.pk}/", "due_at": v.scheduled_start,
        })
    return out


def detect_unsigned_reports():
    from reports.models import CareReport
    cutoff = timezone.now() - timedelta(days=1)
    recent = timezone.now() - timedelta(days=10)
    out = []
    for r in CareReport.objects.filter(signed_by="", created_at__lt=cutoff,
                                       created_at__gte=recent).select_related("visit__client").order_by("-created_at")[:60]:
        cl = r.visit.client if r.visit_id else None
        out.append({
            "source_key": f"unsigned:{r.pk}", "category": "UNSIGNED", "priority": "MEDIUM",
            "title": f"Rapport non signe — {cl.code if cl else 'client'}",
            "detail": f"Rapport du {timezone.localtime(r.created_at):%d/%m} en attente de signature.",
            "link": "/reports/", "due_at": None,
        })
    return out


def detect_hours_to_approve():
    from scheduling.models import Visit, VisitStatus
    n = Visit.objects.filter(status=VisitStatus.COMPLETED, hours_approved=False).count()
    if not n:
        return []
    return [{
        "source_key": "hours:pending", "category": "HOURS",
        "priority": "MEDIUM" if n < 20 else "HIGH",
        "title": f"{n} visite(s) — heures a approuver",
        "detail": "Des heures EVV attendent votre validation avant la paie.",
        "link": "/hours-approval/", "due_at": None,
    }]


def detect_overdue_invoices():
    from clients.models import Invoice
    today = timezone.localdate()
    out = []
    for i in Invoice.objects.select_related("client").all():
        if i.remaining > 0 and (i.due_date or i.issued_date) < today:
            out.append({
                "source_key": f"invoice:{i.pk}", "category": "INVOICE", "priority": "MEDIUM",
                "title": f"{i.client.code} — facture en retard ({i.remaining} $)",
                "detail": f"{i.period} — solde du. Relance / encaissement a prevoir.",
                "link": "/billing/", "due_at": None,
            })
    return out[:500]


ALL_DETECTORS = [detect_cert_expiry, detect_uncovered_visits, detect_unsigned_reports,
                 detect_hours_to_approve, detect_overdue_invoices]


def detect_missing_consent():
    from clients.models import Client, ConsentRecord
    granted = set(ConsentRecord.objects.filter(purpose="CARE", granted=True, withdrawn_at__isnull=True)
                  .values_list("client_id", flat=True))
    out = []
    for c in Client.objects.filter(active=True).exclude(pk__in=granted)[:200]:
        out.append({
            "source_key": f"consent:{c.pk}", "category": "OTHER", "priority": "MEDIUM",
            "title": f"{c.code} — consentement de soins manquant",
            "detail": "Enregistrez le consentement « Prestation des soins » (conformite POPIA/RGPD).",
            "link": f"/clients/{c.pk}/", "due_at": None,
        })
    return out

ALL_DETECTORS = [detect_missing_consent, detect_cert_expiry, detect_uncovered_visits,
                 detect_unsigned_reports, detect_hours_to_approve, detect_overdue_invoices]
