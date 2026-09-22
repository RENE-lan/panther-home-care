def agency(request):
    """Expose agency settings (name, currency…) to every template as `agency`."""
    try:
        from .models import AgencySettings
        return {"agency": AgencySettings.get()}
    except Exception:
        return {"agency": None}


def social_enabled(request):
    """Which social providers are actually configured (so we only show working buttons)."""
    from django.conf import settings
    return {"social_enabled": list((getattr(settings, "SOCIALACCOUNT_PROVIDERS", {}) or {}).keys())}
