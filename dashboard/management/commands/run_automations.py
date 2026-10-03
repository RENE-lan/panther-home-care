"""Panther automations — the rules engine.

Run on demand (button in the app) or nightly via cron:
    python manage.py run_automations

Rules:
  1. Certifications expiring within 30 days  → notify the caregiver.
  2. Visits uncovered within 48h            → run CareMatch, alert coordinators.
  3. Invoices 30+ days overdue              → mark OVERDUE + notify office.
  4. On the 1st of the month                → auto-generate last month's invoices.
"""
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone


def run_rules(force_invoices=False):
    from caregivers.models import Certification
    from clients.models import Client, Invoice
    from scheduling.models import Visit, VisitStatus
    from notifications.models import AlertLevel
    from notifications.services import notify
    from accounts.models import User, Role, AgencySettings
    from ai.services import carematch_ranked

    cfg = AgencySettings.get()
    now = timezone.localtime()
    today = timezone.localdate()
    summary = {"cert_reminders": 0, "uncovered_alerts": 0, "overdue_flagged": 0,
               "invoices_generated": 0}
    if not cfg.automation_enabled:
        return summary  # master switch off (Paramètres → IA & Automatisation)
    coords = list(User.objects.filter(role=Role.COORDINATOR)[:5])

    # 1. Certifications expiring within 30 days (if the alert is enabled)
    if cfg.alert_cert:
        soon = today + timedelta(days=30)
        for c in Certification.objects.filter(expires_on__gte=today, expires_on__lte=soon
                                              ).select_related("caregiver"):
            if c.caregiver.user_id:
                notify(c.caregiver.user, "Certification à renouveler",
                       f"Votre certification « {c.name} » expire le {c.expires_on:%d/%m/%Y}.",
                       level=AlertLevel.ATTENTION, email=cfg.notify_email)
                summary["cert_reminders"] += 1

    # 2. Uncovered visits within 48h → CareMatch (only if auto-replacement rule is on)
    if cfg.auto_replacement:
        for v in Visit.objects.filter(status=VisitStatus.UNCOVERED, scheduled_start__gte=now,
                                      scheduled_start__lt=now + timedelta(hours=48)
                                      ).select_related("client"):
            best = carematch_ranked(v, top_n=1)
            rec = ""
            if best and best[0]["score"] >= cfg.ai_confidence_threshold:
                rec = f" Meilleur profil : {best[0]['caregiver'].code} ({best[0]['score']}%)."
                if cfg.ai_auto_fill:
                    v.caregiver = best[0]["caregiver"]
                    v.status = VisitStatus.SCHEDULED
                    v.save(update_fields=["caregiver", "status"])
                    rec += " Affecté automatiquement."
            for u in coords:
                notify(u, "Visite non couverte imminente",
                       f"{v.client.code} le {timezone.localtime(v.scheduled_start):%d/%m %H:%M}.{rec}",
                       level=AlertLevel.CRITICAL, email=False)
            summary["uncovered_alerts"] += 1

    # 3. Invoices 30+ days overdue → mark OVERDUE + notify office
    if cfg.alert_billing:
        cutoff = today - timedelta(days=30)
        for inv in Invoice.objects.exclude(status="PAID").filter(issued_date__lte=cutoff):
            if inv.status != "OVERDUE":
                inv.status = "OVERDUE"
                inv.save(update_fields=["status"])
            for u in coords:
                notify(u, "Facture en retard",
                       f"{inv.client.code} · {inv.period} · {inv.amount} {cfg.currency} (30+ jours).",
                       level=AlertLevel.ATTENTION, email=False)
            summary["overdue_flagged"] += 1

    # 4. Auto-generate last month's invoices on the 1st (or when forced)
    if today.day == 1 or force_invoices:
        first_this = today.replace(day=1)
        last_month_end = first_this - timedelta(days=1)
        m_start = timezone.make_aware(datetime(last_month_end.year, last_month_end.month, 1))
        m_end = timezone.make_aware(datetime(first_this.year, first_this.month, 1))
        label = m_start.strftime("%B %Y").capitalize()
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
            from decimal import Decimal
            amount = (Decimal(str(round(hours, 1))) * client.bill_rate).quantize(Decimal("0.01"))
            Invoice.objects.create(client=client, period=label, hours=round(hours, 1),
                                   amount=amount, status="DUE", issued_date=today,
                                   due_date=today + timedelta(days=15))
            summary["invoices_generated"] += 1

    return summary


class Command(BaseCommand):
    help = "Run Panther automations (rules engine)."

    def add_arguments(self, parser):
        parser.add_argument("--force-invoices", action="store_true",
                            help="Generate last month's invoices even if not the 1st.")

    def handle(self, *args, **opts):
        s = run_rules(force_invoices=opts.get("force_invoices"))
        self.stdout.write(self.style.SUCCESS(
            f"Automations: {s['cert_reminders']} rappels certif, "
            f"{s['uncovered_alerts']} alertes non-couvert, "
            f"{s['overdue_flagged']} factures en retard, "
            f"{s['invoices_generated']} factures générées."))
