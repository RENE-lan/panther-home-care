"""Panther Priorities — 'what should I do first?'. Ranks every pending action across
the agency by urgency × impact and returns them in order. The AI proposes the order;
the human decides and acts. Cached briefly."""
from datetime import timedelta
from django.utils import timezone
from django.core.cache import cache


def next_actions(limit=6):
    cached = cache.get("next_actions")
    if cached is not None:
        return cached[:limit]
    from scheduling.models import Visit, VisitStatus
    from incidents.models import Incident
    from reports.models import CareReport
    from clients.models import Invoice, ConsentRecord, Client
    from caregivers.models import Certification
    now = timezone.localtime()
    today = timezone.localdate()
    items = []

    def add(score, cat, title, why, link, urgency):
        items.append({"score": score, "cat": cat, "title": title, "why": why,
                      "link": link, "urgency": urgency})

    # 1) Uncovered visits — the more imminent, the more urgent
    for v in (Visit.objects.filter(status=VisitStatus.UNCOVERED, scheduled_start__gte=now,
                                   scheduled_start__lte=now + timedelta(days=2))
              .select_related("client").order_by("scheduled_start")[:20]):
        mins = int((v.scheduled_start - now).total_seconds() // 60)
        score = 100 - min(mins // 30, 40)
        add(score, "UNCOVERED", f"Affecter un soignant — {v.client.code} à {timezone.localtime(v.scheduled_start):%H:%M}",
            f"Visite non couverte, commence dans {mins} min.", "/coverage/", "high")

    # 2) Critical / high open incidents
    for i in (Incident.objects.exclude(status="RESOLVED")
              .filter(severity__in=["CRITICAL", "HIGH"]).select_related("client").order_by("-created_at")[:20]):
        score = 95 if i.severity == "CRITICAL" else 82
        add(score, "INCIDENT", f"Traiter l'incident — {i.title}",
            f"Incident {i.get_severity_display().lower()}{' · ' + i.client.code if i.client else ''}.",
            f"/incidents/{i.id}/", "high")

    # 3) Certifications expiring very soon
    for c in Certification.objects.filter(expires_on__gte=today,
                                          expires_on__lte=today + timedelta(days=14)).select_related("caregiver"):
        days = (c.expires_on - today).days
        add(78 - days, "CERT", f"Renouveler certification — {c.caregiver.full_name}",
            f"{c.name} expire dans {days} j.", "/compliance/", "medium")

    # 4) Overdue invoices (largest first)
    overdue = [i for i in Invoice.objects.select_related("client").all()
               if i.remaining > 0 and (i.due_date or i.issued_date) < today]
    overdue.sort(key=lambda i: i.remaining, reverse=True)
    for i in overdue[:5]:
        add(60, "INVOICE", f"Relancer / encaisser — {i.client.code} ({i.remaining} $)",
            f"Facture {i.period} en retard.", "/billing/", "medium")

    # 5) Hours to approve (batch)
    n_hours = Visit.objects.filter(status=VisitStatus.COMPLETED, hours_approved=False).count()
    if n_hours:
        add(55 if n_hours < 20 else 68, "HOURS", f"Approuver {n_hours} heure(s) EVV",
            "Nécessaire avant la paie.", "/hours-approval/", "medium")

    # 6) Unsigned reports (batch, recent)
    n_unsigned = CareReport.objects.filter(signed_by="", created_at__gte=now - timedelta(days=10)).count()
    if n_unsigned:
        add(45, "UNSIGNED", f"Signer {n_unsigned} rapport(s) de soins",
            "Rapports récents en attente de signature.", "/reports/", "low")

    # 7) Missing care consent
    granted = set(ConsentRecord.objects.filter(purpose="CARE", granted=True, withdrawn_at__isnull=True)
                  .values_list("client_id", flat=True))
    miss = Client.objects.filter(active=True).exclude(id__in=granted).count()
    if miss:
        add(40, "CONSENT", f"Enregistrer le consentement de soins — {miss} client(s)",
            "Conformité POPIA/RGPD.", "/clients/", "low")

    items.sort(key=lambda x: x["score"], reverse=True)
    cache.set("next_actions", items, 45)
    return items[:limit]


def priority_brief(limit=3):
    """One-line-per-item 'start with this' brief for reports / notifications."""
    acts = next_actions(limit)
    if not acts:
        return "Rien d'urgent — tout est à jour. Bonne journée."
    return acts
