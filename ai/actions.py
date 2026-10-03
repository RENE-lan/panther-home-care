"""Actionable Copilot — turns natural language into real CRM operations.
AI proposes → human confirms → Panther executes → Panther records.
Rule-based (works with no API key); an LLM can enrich later."""
import re
from datetime import timedelta
from django.utils import timezone


def _find_lead(term):
    from clients.models import Lead
    from django.db.models import Q
    term = (term or "").strip()
    if not term:
        return None
    qs = Lead.objects.filter(Q(name__icontains=term)).order_by("-created_at")
    return qs.first()


def _find_client(term):
    from clients.models import Client
    from django.db.models import Q
    term = (term or "").strip()
    if not term:
        return None
    return Client.objects.filter(
        Q(first_name__icontains=term) | Q(last_name__icontains=term) | Q(code__icontains=term)
    ).first()


def _target_name(q, after_words):
    """Extract a person's name after a keyword like 'avec', 'le prospect', the verb…"""
    ql = q
    for w in after_words:
        m = re.search(w + r"\s+(.+)", ql, re.IGNORECASE)
        if m:
            name = m.group(1)
            # cut at trailing time/date phrases
            name = re.split(r"\b(demain|aujourd|aujourd'hui|à|a|le |pour|en |vers|cette|ce |la semaine|lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche|\d{1,2}\s*h)\b", name, 1)[0]
            name = name.split(":")[0]
            name = re.sub(r"[?.!,]", "", name).strip()
            for _sw in ("évaluation", "evaluation", "contacté", "contacte", "converti", "perdu", "nouveau", "client"):
                name = re.sub(r"\b" + _sw + r"\b", "", name, flags=re.IGNORECASE).strip()
            _stop = {"le", "la", "les", "prospect", "client", "cliente", "de", "du", "with", "mr", "mme", "m", "madame", "monsieur"}
            name = " ".join(w2 for w2 in name.split() if w2.lower() not in _stop).strip()
            if name:
                return name
    return ""


def _when(q):
    """Parse a rough datetime from the text. Default: tomorrow 10:00."""
    now = timezone.localtime()
    base = now + timedelta(days=1)
    if "aujourd" in q:
        base = now
    jours = {"lundi": 0, "mardi": 1, "mercredi": 2, "jeudi": 3, "vendredi": 4, "samedi": 5, "dimanche": 6}
    for name, wd in jours.items():
        if name in q:
            delta = (wd - now.weekday()) % 7
            delta = delta or 7
            base = now + timedelta(days=delta)
            break
    hh, mm = 10, 0
    m = re.search(r"(\d{1,2})\s*[h:](\s*(\d{2}))?", q)
    if m:
        hh = int(m.group(1))
        mm = int(m.group(3) or 0)
    return base.replace(hour=hh, minute=mm, second=0, microsecond=0)


def parse_action(user, q):
    """Return an action proposal dict, or None if the text isn't a CRM command."""
    ql = (q or "").lower().strip()
    if not ql:
        return None

    # 1) Plan a meeting
    if re.search(r"\b(planifie|planifier|organise|organiser|réunion|reunion|rendez-vous|rdv|meeting)\b", ql):
        name = _target_name(q, [r"avec", r"pour", r"réunion\s+avec", r"reunion\s+avec", r"rdv\s+avec"])
        cl = _find_client(name) if name else None
        when = _when(ql)
        return {"kind": "meeting", "label": "Planifier une réunion",
                "detail": f"{'avec ' + cl.full_name if cl else 'réunion'} · {when:%d/%m à %H:%M}".capitalize(),
                "params": {"client_id": cl.id if cl else None, "client_name": cl.full_name if cl else (name or "—"),
                           "when": when.isoformat(), "title": f"Réunion {cl.full_name if cl else name}".strip()}}

    # 2) Advance a prospect stage
    stages = {"contacté": "CONTACTED", "contacte": "CONTACTED", "évaluation": "ASSESSMENT",
              "evaluation": "ASSESSMENT", "perdu": "LOST", "converti": "CONVERTED", "nouveau": "NEW"}
    if re.search(r"\b(passe|avance|déplace|deplace|mets?|change)\b", ql) and any(s in ql for s in stages):
        name = _target_name(q, [r"prospect", r"passe", r"avance", r"déplace", r"deplace"])
        lead = _find_lead(name)
        tgt = next((v for k, v in stages.items() if k in ql), None)
        if lead and tgt:
            from clients.models import Lead
            label = dict(Lead.Stage.choices).get(tgt, tgt)
            return {"kind": "lead_stage", "label": "Changer l'étape du prospect",
                    "detail": f"{lead.name} → {label}",
                    "params": {"lead_id": lead.id, "lead_name": lead.name, "stage": tgt, "stage_label": label}}

    # 3) Convert a prospect to client
    if re.search(r"\b(convertis|convertir|convert)\b", ql) or "passe en client" in ql:
        name = _target_name(q, [r"convertis", r"convertir", r"prospect", r"client"])
        lead = _find_lead(name)
        if lead and not lead.converted_client_id:
            return {"kind": "lead_convert", "label": "Convertir en client",
                    "detail": f"{lead.name} deviendra un client (historique conservé)",
                    "params": {"lead_id": lead.id, "lead_name": lead.name}}

    # 4) Follow up / contact a prospect
    if re.search(r"\b(relance|relancer|rappelle|rappeler|contacte|contacter|appelle|appeler|suivi|suis)\b", ql):
        name = _target_name(q, [r"relance", r"relancer", r"rappelle", r"rappeler", r"contacte", r"contacter",
                                r"appelle", r"appeler", r"suivi\s+de", r"prospect"])
        lead = _find_lead(name)
        if lead:
            return {"kind": "lead_followup", "label": "Relancer le prospect",
                    "detail": f"Enregistrer une relance pour {lead.name} + prochaine action",
                    "params": {"lead_id": lead.id, "lead_name": lead.name}}

    # 5) Create a task / note on a prospect
    if re.search(r"\b(tâche|tache|note|rappel|à faire|a faire)\b", ql):
        name = _target_name(q, [r"pour", r"prospect", r"client", r"sur"])
        lead = _find_lead(name)
        if lead:
            note = (q.split(":", 1)[1].strip() if ":" in q else
                    re.sub(r".*(tâche|tache|note|rappel)\s*", "", q, 1, flags=re.IGNORECASE).strip()) or "Tâche de suivi"
            return {"kind": "lead_task", "label": "Créer une tâche",
                    "detail": f"{lead.name} : {note[:60]}",
                    "params": {"lead_id": lead.id, "lead_name": lead.name, "note": note[:120]}}
    return None


def execute_action(user, action):
    """Perform a confirmed action and record it. Returns {ok, message, link}."""
    from clients.models import Lead, LeadEvent
    kind = action.get("kind")
    p = action.get("params", {})
    try:
        if kind == "lead_followup":
            lead = Lead.objects.get(pk=p["lead_id"])
            LeadEvent.objects.create(lead=lead, kind="CALL", actor=user, note="Relance (via copilote)")
            lead.next_action = f"Rappeler {lead.name}"
            if lead.stage == "NEW":
                lead.stage = "CONTACTED"
            lead.save()
            return {"ok": True, "message": f"Relance enregistrée pour {lead.name}. Prochaine action : rappeler.",
                    "link": f"/leads/{lead.id}/"}

        if kind == "lead_stage":
            lead = Lead.objects.get(pk=p["lead_id"])
            lead.stage = p["stage"]
            lead.save()
            LeadEvent.objects.create(lead=lead, kind="STAGE", actor=user, note=f"Étape : {p.get('stage_label')}")
            return {"ok": True, "message": f"{lead.name} est passé à « {p.get('stage_label')} ».",
                    "link": f"/leads/{lead.id}/"}

        if kind == "lead_convert":
            lead = Lead.objects.get(pk=p["lead_id"])
            if lead.converted_client_id:
                return {"ok": True, "message": "Déjà converti.", "link": f"/clients/{lead.converted_client_id}/"}
            # reuse the same carry-over logic as the web convert
            from clients.models import Client
            nums = [int("".join(ch for ch in c if ch.isdigit()) or 0) for c in Client.objects.values_list("code", flat=True)]
            parts = lead.name.split(" ", 1)
            client = Client.objects.create(
                code=f"Client #{(max(nums) + 1) if nums else 1:03d}",
                first_name=parts[0], last_name=parts[1] if len(parts) > 1 else "",
                care_type=lead.care_need or "Soins à domicile", active=True,
                notes=f"Converti depuis prospect (copilote). Source : {lead.referred_by or lead.source}")
            if lead.phone:
                client.contacts.create(name=lead.name, phone=lead.phone, relationship="Prospect", is_primary=True)
            lead.stage = "CONVERTED"
            lead.converted_client = client
            lead.save()
            LeadEvent.objects.create(lead=lead, kind="STAGE", actor=user, note=f"Converti en {client.code} (copilote)")
            return {"ok": True, "message": f"{lead.name} est désormais {client.code}.", "link": f"/clients/{client.id}/"}

        if kind == "lead_task":
            lead = Lead.objects.get(pk=p["lead_id"])
            lead.next_action = p["note"]
            lead.save()
            LeadEvent.objects.create(lead=lead, kind="NOTE", actor=user, note=p["note"])
            return {"ok": True, "message": f"Tâche ajoutée à {lead.name}.", "link": f"/leads/{lead.id}/"}

        if kind == "meeting":
            from collab.models import Meeting
            from datetime import datetime
            when = datetime.fromisoformat(p["when"])
            m = Meeting.objects.create(title=p.get("title") or "Réunion", requested_by=user,
                                       proposed_at=when, duration_min=30,
                                       client_id=p.get("client_id"))
            return {"ok": True, "message": f"Réunion créée : {p.get('title')} ({when:%d/%m %H:%M}).",
                    "link": f"/collab/meetings/{m.id}/room/"}
    except Exception as e:
        return {"ok": False, "message": f"Impossible d'exécuter : {e}", "link": ""}
    return {"ok": False, "message": "Action inconnue.", "link": ""}
