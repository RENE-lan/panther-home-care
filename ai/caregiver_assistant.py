"""Assistant Panther IA (soignant, mobile) — répond à tout, ancré sur la tournée du soignant.
Garde-fous : aucune décision médicale (posologie, diagnostic, changement de traitement) —
ces cas sont escaladés au coordinateur / à l'infirmier(e)."""
import os
import json
from django.utils import timezone

_CLINICAL = ["posologie", "dose", "diagnos", "prescri", "ordonnance", "changer le traitement",
             "augmenter la dose", "réduire la dose", "quel médicament", "puis-je donner",
             "dosage", "symptôme grave", "urgence vitale"]


def snapshot(cg):
    from scheduling.models import Visit, VisitStatus
    now = timezone.localtime()
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week = day - timezone.timedelta(days=day.weekday())
    today = cg.visits.filter(scheduled_start__gte=day, scheduled_start__lt=day + timezone.timedelta(days=1))
    nxt = cg.visits.filter(status=VisitStatus.SCHEDULED, scheduled_start__gte=now).select_related("client").order_by("scheduled_start").first()
    hrs = round(sum((v.check_out_at - v.check_in_at).total_seconds() / 3600
                    for v in cg.visits.filter(status=VisitStatus.COMPLETED, scheduled_start__gte=week)
                    if v.check_in_at and v.check_out_at), 1)
    data = {"name": cg.full_name, "today_visits": today.count(),
            "hours_this_week": hrs, "punctuality": getattr(cg, "punctuality_score", None)}
    if nxt:
        data["next_visit"] = {"when": timezone.localtime(nxt.scheduled_start).strftime("%H:%M"),
                              "client": nxt.client.code, "care": nxt.client.care_type or "soins"}
    exp = cg.certifications.filter(expires_on__lt=timezone.localdate()).count()
    if exp:
        data["expired_certs"] = exp
    return data


SYSTEM = (
    "Tu es l'Assistant Panther IA du soignant, sur mobile. Tu réponds avec bienveillance et concision, "
    "en français par défaut. Tu réponds à TOUTES les questions : la tournée du jour et le planning "
    "(en t'appuyant sur le CONTEXTE), l'aide à la rédaction de notes de visite, les bonnes pratiques "
    "générales de soins à domicile, et les questions générales. Garde-fou strict : tu ne prends JAMAIS "
    "de décision médicale (posologie, diagnostic, modification de traitement) — dans ces cas, tu invites "
    "le soignant à contacter le coordinateur ou l'infirmier(e). N'invente pas d'information absente du contexte.")


def answer(cg, question, history=None):
    snap = snapshot(cg)
    if any(t in (question or "").lower() for t in _CLINICAL):
        return {"answer": ("Cette question relève d'une décision médicale. Pour la sécurité du bénéficiaire, "
                           "contactez le coordinateur ou l'infirmier(e) référent(e) avant d'agir."),
                "escalated": True}
    try:
        from ai import llm
        if llm.available():
            system = SYSTEM + "\n\nCONTEXTE (tournée du soignant) : " + json.dumps(snap, ensure_ascii=False)
            msgs = []
            for m in (history or [])[-8:]:
                role = "assistant" if m.get("role") == "assistant" else "user"
                c = (m.get("content") or "").strip()
                if c:
                    msgs.append({"role": role, "content": c})
            msgs.append({"role": "user", "content": question})
            out = llm.chat(msgs, system=system, max_tokens=500)
            if out and out.strip():
                return {"answer": out.strip(), "escalated": False}
    except Exception:
        pass
    # deterministic fallback (no key)
    bits = []
    if snap.get("next_visit"):
        nv = snap["next_visit"]; bits.append(f"Prochaine visite {nv['when']} — {nv['client']} ({nv['care']}).")
    if snap.get("today_visits"):
        bits.append(f"{snap['today_visits']} visite(s) aujourd'hui.")
    if snap.get("hours_this_week") is not None:
        bits.append(f"{snap['hours_this_week']} h cette semaine.")
    if snap.get("expired_certs"):
        bits.append(f" {snap['expired_certs']} certification(s) expirée(s) — pensez à renouveler.")
    return {"answer": " ".join(bits) or "Je peux vous aider sur votre planning, vos visites et vos notes de soins. Que souhaitez-vous ?", "escalated": False}
