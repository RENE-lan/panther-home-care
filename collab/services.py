import os
from django.utils import timezone
from .models import WorkItem, WorkItemEvent
from .detectors import ALL_DETECTORS


def run_scan():
    seen, scanned_cats = set(), set()
    created = updated = closed = 0
    for det in ALL_DETECTORS:
        for r in (det() or []):
            scanned_cats.add(r["category"]); seen.add(r["source_key"])
            obj, made = WorkItem.objects.get_or_create(
                source_key=r["source_key"],
                defaults=dict(category=r["category"], priority=r.get("priority", "MEDIUM"),
                              title=r["title"], detail=r.get("detail", ""), link=r.get("link", ""),
                              due_at=r.get("due_at"), status="OPEN"))
            if made:
                created += 1; WorkItemEvent.objects.create(item=obj, action="created")
            else:
                changed = False
                for f in ("priority", "title", "detail", "link", "due_at"):
                    if getattr(obj, f) != r.get(f, getattr(obj, f)):
                        setattr(obj, f, r.get(f, getattr(obj, f))); changed = True
                if obj.status == "SNOOZED" and obj.snooze_until and obj.snooze_until <= timezone.now():
                    obj.status = "OPEN"; changed = True
                if changed:
                    obj.save(); updated += 1
    stale = WorkItem.objects.filter(status__in=["OPEN", "SNOOZED"],
                                    category__in=scanned_cats).exclude(source_key__in=seen)
    for obj in stale:
        obj.status = "RESOLVED"; obj.resolved_at = timezone.now(); obj.decision_note = "Condition resolue (auto)"
        obj.save(update_fields=["status", "resolved_at", "decision_note"])
        WorkItemEvent.objects.create(item=obj, action="auto_resolved"); closed += 1
    return {"created": created, "updated": updated, "auto_closed": closed}


def workload_summary(items):
    if not items:
        return "Rien ne requiert votre attention pour le moment."
    by = {}
    for it in items:
        by[it.category] = by.get(it.category, 0) + 1
    label = {"CERT": "certification(s)", "UNCOVERED": "visite(s) non couverte(s)",
             "UNSIGNED": "rapport(s) non signe(s)", "HOURS": "heures a approuver",
             "INVOICE": "facture(s) en retard", "FOLLOWUP": "relance(s)", "OTHER": "autre(s)"}
    parts = [f"{v} {label.get(k, k.lower())}" for k, v in by.items()]
    base = f"{len(items)} element(s) a traiter : " + ", ".join(parts) + "."
    key = os.environ.get("AI_API_KEY")
    if not key:
        return base
    try:
        import urllib.request, json
        top = "; ".join(it.title for it in items[:8])
        prompt = ("Assistant d'un coordinateur de soins a domicile. Resume en une phrase claire, en francais, "
                  "le travail prioritaire du jour. Ne decide rien, propose seulement. Elements: " + top)
        prov = os.environ.get("AI_PROVIDER", "anthropic")
        if prov == "anthropic":
            req = urllib.request.Request("https://api.anthropic.com/v1/messages",
                data=json.dumps({"model": os.environ.get("AI_MODEL", "claude-3-5-sonnet-latest"), "max_tokens": 120,
                                 "messages": [{"role": "user", "content": prompt}]}).encode(),
                headers={"content-type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01"})
            with urllib.request.urlopen(req, timeout=12) as rr:
                return json.loads(rr.read())["content"][0]["text"].strip() or base
        req = urllib.request.Request("https://api.openai.com/v1/chat/completions",
            data=json.dumps({"model": os.environ.get("AI_MODEL", "gpt-4o-mini"), "max_tokens": 120,
                             "messages": [{"role": "user", "content": prompt}]}).encode(),
            headers={"content-type": "application/json", "authorization": f"Bearer {key}"})
        with urllib.request.urlopen(req, timeout=12) as rr:
            return json.loads(rr.read())["choices"][0]["message"]["content"].strip() or base
    except Exception:
        return base
