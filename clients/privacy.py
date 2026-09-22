"""Consent + data-access helpers. Flat, no abstraction layers."""
from django.utils import timezone
from .models import ConsentRecord, DataAccessLog


def log_access(actor, client, what="Consultation du dossier"):
    if client is None:
        return
    DataAccessLog.objects.create(
        client=client, actor=actor if getattr(actor, "pk", None) else None,
        actor_name=(actor.get_full_name() or actor.username) if getattr(actor, "pk", None) else "Système",
        actor_role=getattr(actor, "get_role_display", lambda: "")() if getattr(actor, "pk", None) else "",
        what=what)


def consent_status(client):
    """Return the full purpose list with current state (for staff + family views)."""
    existing = {c.purpose: c for c in client.consents.all()}
    rows = []
    for code, label in ConsentRecord.PURPOSES:
        c = existing.get(code)
        rows.append({"code": code, "label": label,
                     "granted": bool(c and c.active),
                     "withdrawn": bool(c and c.withdrawn_at),
                     "at": (c.granted_at if c else None), "obj": c})
    return rows


def set_consent(client, purpose, granted, actor=None, signed_by="", signature=""):
    c, _ = ConsentRecord.objects.get_or_create(client=client, purpose=purpose)
    if granted:
        c.granted = True; c.granted_at = timezone.now(); c.withdrawn_at = None
    else:
        c.withdrawn_at = timezone.now()
    if signed_by:
        c.signed_by = signed_by
    if signature:
        c.signature = signature
    c.recorded_by = actor if getattr(actor, "pk", None) else None
    c.save()
    return c
