from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Immutable-ish record of who did what, when — accountability across the platform."""
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="audit_entries")
    action = models.CharField(max_length=200)
    target = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        who = self.actor.get_username() if self.actor else "système"
        return f"{self.created_at:%d %b %H:%M} · {who} · {self.action}"


def log(actor, action, target=""):
    """Tiny helper so any view/service can record an audit entry in one line."""
    return AuditLog.objects.create(actor=actor if getattr(actor, "is_authenticated", False) else None,
                                   action=action, target=str(target))
