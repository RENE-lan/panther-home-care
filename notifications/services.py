"""Multi-channel notification delivery: in-app + email + optional SMS.

notify(recipient, title, body, ...) always creates an in-app Notification, sends an
email if the user has an address, and sends an SMS if Twilio credentials are configured
(TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_FROM) and the user has a phone number.
Everything is best-effort and never raises — delivery must not break a request.
"""
import json
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.mail import send_mail

from .models import AlertLevel, Notification


def _send_email(user, title, body):
    if not getattr(user, "email", ""):
        return False
    try:
        send_mail(subject=f"[Panther Home Care] {title}", message=body,
                  from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@panthergroup.cd"),
                  recipient_list=[user.email], fail_silently=True)
        return True
    except Exception:
        return False


def _send_sms(phone, body):
    sid = getattr(settings, "TWILIO_ACCOUNT_SID", "")
    token = getattr(settings, "TWILIO_AUTH_TOKEN", "")
    frm = getattr(settings, "TWILIO_FROM", "")
    if not (sid and token and frm and phone):
        return False
    try:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        data = urllib.parse.urlencode({"To": phone, "From": frm, "Body": body}).encode()
        req = urllib.request.Request(url, data=data)
        auth = __import__("base64").b64encode(f"{sid}:{token}".encode()).decode()
        req.add_header("Authorization", f"Basic {auth}")
        urllib.request.urlopen(req, timeout=8)
        return True
    except Exception:
        return False


def notify(recipient, title, body="", level=AlertLevel.INFO,
           email=True, sms=False, link=""):
    """Deliver a notification to one user across the requested channels.
    Returns a dict of which channels succeeded."""
    result = {"in_app": False, "email": False, "sms": False}
    try:
        Notification.objects.create(recipient=recipient, level=level,
                                    title=title, body=body)
        result["in_app"] = True
    except Exception:
        pass
    if email:
        result["email"] = _send_email(recipient, title, body)
    if sms:
        phone = getattr(recipient, "phone", "") or ""
        result["sms"] = _send_sms(phone, f"{title}. {body}")
    return result
