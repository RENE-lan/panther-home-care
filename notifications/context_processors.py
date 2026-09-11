def unread_alerts(request):
    """Expose unread-alert count to every template (for the bell badge)."""
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {"unread_alert_count": 0}
    from .models import Notification
    count = Notification.objects.filter(recipient=request.user, read=False).count()
    return {"unread_alert_count": count}
