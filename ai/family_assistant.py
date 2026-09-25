"""Assistant Panther IA (famille) — ancré sur les données de soins du proche.
Principe : l'IA informe et oriente ; elle ne donne JAMAIS de conseil médical.
Toute question clinique est renvoyée au coordinateur / à l'infirmier(e)."""
import os
import json
from django.utils import timezone

_CLINICAL = ["médic", "medic", "dose", "traitement", "symptôme", "symptome", "douleur",
             "diagnos", "maladie", "urgence", "tension", "santé se dégrade", "should i give",
             "posologie", "ordonnance", "effet secondaire"]


def snapshot(client):
    """Compact, grounded view of the loved one's care — no clinical judgement."""
    from scheduling.models import Visit, VisitStatus
    from reports.models import CareReport
    from clients.models import Invoice
    now = timezone.localtime()
    data = {"name": client.first_name}
    nxt = (Visit.objects.filter(client=client, status=VisitStatus.SCHEDULED, scheduled_start__gte=now)
           .select_related("caregiver").order_by("scheduled_start").first())
    if nxt:
        data["next_visit"] = {
            "when": timezone.localtime(nxt.scheduled_start).strftime("%d/%m %H:%M"),
            "caregiver": nxt.caregiver.full_name if nxt.caregiver else "à confirmer"}
    last = (CareReport.objects.filter(visit__client=client).select_related("visit")
            .order_by("-created_at").first())
    if last:
        data["last_report"] = {"when": timezone.localtime(last.created_at).strftime("%d/%m"),
                               "summary": (getattr(last, "summary", "") or "")[:200]}
    inv = list(Invoice.objects.filter(client=client))
    outstanding = sum(i.remaining for i in inv)
    if outstanding:
        data["outstanding"] = f"{outstanding} $"
    week = Visit.objects.filter(client=client, scheduled_start__gte=now,
                                scheduled_start__lte=now + timezone.timedelta(days=7)).count()
    data["visits_next_7d"] = week
    return data


def _actions(question, snap):
    q = (question or "").lower()
    out = []
    if any(t in q for t in _CLINICAL) or "coordin" in q or "infirm" in q:
        out.append({"key": "contact_coordinator", "label": "Contacter le coordinateur"})
    if "rapport" in q or "report" in q or "soin" in q:
        out.append({"key": "view_reports", "label": "Voir les rapports"})
    if "factur" in q or "payer" in q or "solde" in q or snap.get("outstanding"):
        out.append({"key": "view_invoices", "label": "Voir les factures"})
    if "visite" in q or "planning" in q or "quand" in q:
        out.append({"key": "view_visits", "label": "Voir le planning"})
    seen, res = set(), []
    for a in out:
        if a["key"] not in seen:
            seen.add(a["key"]); res.append(a)
    return res[:3]


def answer(client, question, history=None):
    snap = snapshot(client)
    clinical = any(t in (question or "").lower() for t in _CLINICAL)
    # Guardrail: clinical/medical questions are always routed to the coordinator.
    if clinical:
        return {"answer": _fallback(question, snap, True),
                "actions": _actions(question, snap), "routed_to_coordinator": True}
    # Otherwise Claude answers anything (care logistics + general questions).
    try:
        from ai import llm
        if llm.available():
            import json as _json
            system = (SYSTEM + "\n\nCONTEXTE (données du proche, à utiliser sans rien inventer) : "
                      + _json.dumps(snap, ensure_ascii=False))
            msgs = []
            for m in (history or [])[-8:]:
                role = "assistant" if m.get("role") == "assistant" else "user"
                c = (m.get("content") or "").strip()
                if c:
                    msgs.append({"role": role, "content": c})
            msgs.append({"role": "user", "content": question})
            out = llm.chat(msgs, system=system, max_tokens=500)
            if out and out.strip():
                return {"answer": out.strip(), "actions": _actions(question, snap), "routed_to_coordinator": False}
    except Exception:
        pass
    return {"answer": _fallback(question, snap, False),
            "actions": _actions(question, snap), "routed_to_coordinator": False}


def _fallback(question, snap, clinical):
    if clinical:
        return ("Pour toute question de santé, de médication ou de symptômes, je préfère vous orienter "
                "vers le coordinateur de soins, qui pourra vous répondre en toute sécurité. "
                "Souhaitez-vous le contacter ?")
    bits = []
    if snap.get("next_visit"):
        bits.append(f"Prochaine visite : {snap['next_visit']['when']} avec {snap['next_visit']['caregiver']}.")
    if snap.get("visits_next_7d"):
        bits.append(f"{snap['visits_next_7d']} visite(s) prévue(s) cette semaine.")
    if snap.get("last_report", {}).get("summary"):
        bits.append(f"Dernier rapport ({snap['last_report']['when']}) : {snap['last_report']['summary']}")
    if snap.get("outstanding"):
        bits.append(f"Solde à régler : {snap['outstanding']}.")
    if not bits:
        return (f"Je peux vous renseigner sur les soins de {snap.get('name','votre proche')} : "
                "visites, rapports, équipe et factures. Que souhaitez-vous savoir ?")
    return " ".join(bits)


SYSTEM = (
    "Tu es l'Assistant Panther IA pour la famille d'un bénéficiaire de soins à domicile. "
    "Tu réponds avec chaleur et clarté, en français par défaut (ou dans la langue de la question). "
    "Tu réponds à TOUTES les questions : celles sur les soins du proche (en t'appuyant sur le CONTEXTE : "
    "visites, rapports, équipe, factures) ET les questions générales (rédiger un message, expliquer un terme, "
    "traduire, aider à s'organiser). Règle stricte et non négociable : tu ne donnes JAMAIS de conseil médical, "
    "de posologie, ni d'interprétation de symptômes — pour cela tu orientes vers le coordinateur de soins. "
    "N'invente jamais d'information sur le proche absente du CONTEXTE ; si tu ne l'as pas, dis-le. Sois concis.")


def _llm(question, snap):
    import urllib.request
    key = os.environ["AI_API_KEY"]
    prompt = SYSTEM + "\n\nCONTEXTE:\n" + json.dumps(snap, ensure_ascii=False) + "\n\nQUESTION: " + (question or "")
    prov = os.environ.get("AI_PROVIDER", "anthropic")
    try:
        if prov == "anthropic":
            req = urllib.request.Request("https://api.anthropic.com/v1/messages",
                data=json.dumps({"model": os.environ.get("AI_MODEL", "claude-3-5-sonnet-latest"), "max_tokens": 250,
                                 "messages": [{"role": "user", "content": prompt}]}).encode(),
                headers={"content-type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01"})
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read())["content"][0]["text"].strip()
        req = urllib.request.Request("https://api.openai.com/v1/chat/completions",
            data=json.dumps({"model": os.environ.get("AI_MODEL", "gpt-4o-mini"), "max_tokens": 250,
                             "messages": [{"role": "system", "content": SYSTEM},
                                          {"role": "user", "content": prompt}]}).encode(),
            headers={"content-type": "application/json", "authorization": f"Bearer {key}"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())["choices"][0]["message"]["content"].strip()
    except Exception:
        return None
