def agency(request):
    """Expose agency settings (name, currency…) to every template as `agency`."""
    try:
        from .models import AgencySettings
        return {"agency": AgencySettings.get()}
    except Exception:
        return {"agency": None}
