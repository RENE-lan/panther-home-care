"""End-to-end client journey — proves the modules share the same records.
Lead → Client → Assessment → Care plan → Visit → Caregiver → EVV → Notes →
Completed → Hours → Invoice → Payment → Profitability → AI insight."""
from django.utils import timezone


def client_journey(client):
    from scheduling.models import Visit, VisitStatus
    from reports.models import CareReport
    from clients.models import Lead, Invoice
    v = client.visits.all()

    def ok(q):
        try:
            return q()
        except Exception:
            return False

    was_lead = ok(lambda: Lead.objects.filter(converted_client=client).exists())
    has_assess = ok(lambda: client.assessments.exists())
    has_plan = ok(lambda: bool(getattr(client, "care_plan", None))) or bool(client.care_type)
    has_visit = ok(lambda: v.exists())
    has_cg = ok(lambda: v.filter(caregiver__isnull=False).exists())
    has_evv = ok(lambda: v.filter(check_in_at__isnull=False).exists())
    has_notes = ok(lambda: CareReport.objects.filter(visit__client=client).exists())
    has_done = ok(lambda: v.filter(status=VisitStatus.COMPLETED).exists())
    has_hours = ok(lambda: v.filter(status=VisitStatus.COMPLETED, hours_approved=True).exists())
    invs = list(client.invoices.all())
    has_invoice = len(invs) > 0
    has_payment = any((i.amount_paid or 0) > 0 for i in invs)
    has_profit = has_invoice  # revenue known → margin computable
    try:
        from ai.attention import attention_for_client
        has_ai = attention_for_client(client) is not None or client.concerns.exists()
    except Exception:
        has_ai = client.concerns.exists()

    done_count = v.filter(status=VisitStatus.COMPLETED).count()
    stages = [
        ("Prospect", was_lead, "Issu du CRM" if was_lead else "Client direct", "/leads/"),
        ("Client", client.active, client.code, f"/clients/{client.id}/"),
        ("Évaluation", has_assess, "Évaluation réalisée" if has_assess else "À planifier", f"/clients/{client.id}/"),
        ("Plan de soins", has_plan, client.care_type or "—", f"/clients/{client.id}/"),
        ("Visites", has_visit, f"{v.count()} planifiée(s)", "/schedule/"),
        ("Soignant", has_cg, "Affecté" if has_cg else "Non couvert", "/coverage/"),
        ("EVV / Pointage", has_evv, "Pointages enregistrés" if has_evv else "En attente", "/live/"),
        ("Notes de soins", has_notes, "Documentées" if has_notes else "—", "/reports/"),
        ("Visite terminée", has_done, f"{done_count} terminée(s)", "/reports/"),
        ("Heures approuvées", has_hours, "Validées" if has_hours else "À approuver", "/hours-approval/"),
        ("Facture", has_invoice, f"{len(invs)} facture(s)" if has_invoice else "—", "/billing/"),
        ("Paiement", has_payment, "Encaissé" if has_payment else "En attente", "/billing/"),
        ("Rentabilité", has_profit, "Marge calculée" if has_profit else "—", "/billing/"),
        ("Insight IA", has_ai, "Signaux détectés" if has_ai else "RAS", f"/clients/{client.id}/"),
    ]
    reached = sum(1 for _, d, _, _ in stages if d)
    return {"stages": [{"label": l, "done": d, "detail": det, "link": lk}
                       for l, d, det, lk in stages],
            "reached": reached, "total": len(stages),
            "pct": round(reached / len(stages) * 100)}
