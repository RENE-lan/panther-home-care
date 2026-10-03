"""Prospect Intelligence — qualifies a lead and connects CRM → operations → finance.
Estimates care hours, monthly value & margin, conversion potential, caregiver
availability and the recommended next action. Estimates only; the human decides."""
from django.utils import timezone


def _hours_per_day(care_need):
    t = (care_need or "").lower()
    if any(k in t for k in ["24", "live-in", "permanent", "continu", "nuit"]):
        return 12
    if any(k in t for k in ["mobilit", "personnel", "hygiène", "hygiene", "toilette", "nursing", "infirm"]):
        return 4
    if any(k in t for k in ["compagnie", "companion", "ménage", "menage", "course"]):
        return 3
    return 4


def prospect_intelligence(lead):
    from accounts.models import AgencySettings
    from caregivers.models import Caregiver
    cfg = AgencySettings.get()
    cur = getattr(cfg, "currency", "R") or "R"
    bill = float(getattr(cfg, "default_bill_rate", 0) or 8)
    hpd = _hours_per_day(lead.care_need)
    monthly_hours = hpd * 30
    monthly_value = round(bill * monthly_hours)

    pays = [float(c.pay_rate) for c in Caregiver.objects.filter(active=True) if getattr(c, "pay_rate", None)]
    avg_pay = round(sum(pays) / len(pays), 2) if pays else round(bill * 0.55, 2)
    margin_per_h = max(bill - avg_pay, 0)
    monthly_margin = round(margin_per_h * monthly_hours)
    margin_pct = round(margin_per_h / bill * 100) if bill else 0

    # conversion potential
    score = {"NEW": 40, "CONTACTED": 60, "ASSESSMENT": 80, "CONVERTED": 100, "LOST": 0}.get(lead.stage, 40)
    src = (getattr(lead, "source", "") or "").upper()
    if "REFERRAL" in src or (lead.referred_by or ""):
        score += 15
    if lead.phone:
        score += 5
    try:
        score += min(lead.events.count() * 5, 15)
    except Exception:
        pass
    score = min(score, 100)
    level = "high" if score >= 75 else ("medium" if score >= 50 else "low")

    available = Caregiver.objects.filter(active=True).count()
    matches = min(available, 3)

    if lead.next_action:
        next_action = lead.next_action
    else:
        next_action = {"NEW": "Contacter le prospect", "CONTACTED": "Planifier l'évaluation",
                       "ASSESSMENT": "Finaliser l'évaluation et convertir"}.get(lead.stage, "Faire le suivi")

    deadline = {"NEW": "Aujourd'hui", "CONTACTED": "Sous 48 h", "ASSESSMENT": "Cette semaine"}.get(lead.stage, "—")

    return {
        "level": level, "score": score,
        "care_requirement": lead.care_need or "À évaluer",
        "hours_per_day": hpd, "cur": cur,
        "monthly_value": f"{cur} {monthly_value:,}".replace(",", " "),
        "monthly_margin": f"{cur} {monthly_margin:,}".replace(",", " "),
        "margin_pct": margin_pct,
        "next_action": next_action,
        "matches": matches, "available": available,
        "deadline": deadline,
    }
