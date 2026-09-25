"""Role → module access engine. Admin can override via the AccessMatrix; sensible
defaults apply otherwise. ADMIN and MANAGER always see everything."""

# Modules that can be gated (key, label)
AREAS = [
    ("clients", "Clients (dossiers)"),
    ("clinical", "Suivi clinique"),
    ("care_insights", "Care Insights"),
    ("scheduling", "Planification"),
    ("coverage", "Couverture"),
    ("incidents", "Incidents"),
    ("reports", "Rapports de soins"),
    ("caregivers", "Soignants / Personnel"),
    ("recruitment", "Recrutement"),
    ("compliance", "Conformité"),
    ("billing", "Facturation & paie"),
    ("finance_analytics", "Analytique financière"),
    ("messages_care", "Messages — Soins"),
    ("messages_finance", "Messages — Finance"),
    ("meetings", "Réunions"),
    ("communications", "Diffusions"),
    ("users_admin", "Utilisateurs & accès"),
]
AREA_KEYS = [a for a, _ in AREAS]

# Configurable office roles (CAREGIVER/FAMILY use their own portals, not this matrix)
ROLES = [("COORDINATOR", "Coordinateur"), ("SUPERVISOR", "Superviseur"),
         ("FINANCE", "Finance"), ("CLINICAL", "Conseiller clinique")]
ROLE_KEYS = [r for r, _ in ROLES]

_ALL = set(AREA_KEYS)
DEFAULTS = {
    "COORDINATOR": _ALL - {"billing", "finance_analytics", "messages_finance", "users_admin"},
    "SUPERVISOR": {"clients", "clinical", "care_insights", "scheduling", "incidents",
                   "reports", "caregivers", "messages_care", "meetings"},
    "FINANCE": {"clients", "billing", "finance_analytics", "messages_finance", "meetings"},
    "CLINICAL": {"clients", "clinical", "care_insights", "incidents", "reports",
                 "messages_care", "meetings"},
}


def can(user, area):
    if not getattr(user, "is_authenticated", False):
        return False
    role = getattr(user, "role", "") or ""
    if getattr(user, "is_superuser", False) or role in ("ADMIN", "MANAGER"):
        return True
    from .models import AccessMatrix
    data = (AccessMatrix.get().data or {}).get(role)
    if isinstance(data, dict) and area in data:
        return bool(data[area])
    return area in DEFAULTS.get(role, set())


def perms_for(user):
    role = getattr(user, "role", "") or ""
    if getattr(user, "is_superuser", False) or role in ("ADMIN", "MANAGER"):
        return set(AREA_KEYS)
    return {a for a in AREA_KEYS if can(user, a)}
