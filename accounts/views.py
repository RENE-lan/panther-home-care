"""Social sign-in gate.

Each provider button routes here. If the provider's real OAuth credentials are
configured, we hand off to the genuine allauth flow; otherwise we show a clean,
branded "not yet configured" page instead of an error.
"""
from django.conf import settings
from django.shortcuts import redirect, render

_PROVIDERS = {"google": "Google", "apple": "Apple", "facebook": "Facebook"}


def admin_login_redirect(request):
    """Send the Django admin login through the single branded login page.

    Avoids the separate admin login (and its occasional first-attempt token issue),
    and gives one consistent sign-in for the whole app.
    """
    from django.shortcuts import redirect
    nxt = request.GET.get("next", "/admin/")
    if request.user.is_authenticated and not request.user.is_staff:
        # Logged in but not an admin — don't loop; send them to their space.
        return redirect("dashboard:home")
    return redirect(f"/accounts/login/?next={nxt}")


def social_start(request, provider):
    provider = provider.lower()
    if provider not in _PROVIDERS:
        return redirect("account_login")
    if provider in getattr(settings, "SOCIALACCOUNT_PROVIDERS", {}):
        return redirect(f"/accounts/{provider}/login/?process=login")
    return render(request, "account/social_unconfigured.html",
                  {"provider": _PROVIDERS[provider]}, status=200)
