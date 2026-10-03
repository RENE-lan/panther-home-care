"""allauth adapters.

New self-service sign-ups (email or social) land as Coordinators so they can explore
the platform immediately. In production you'd instead create staff accounts with the
right role and let families self-register into a FAMILY role — change DEFAULT_SIGNUP_ROLE
below, or route by invitation.
"""
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from accounts.models import Role

DEFAULT_SIGNUP_ROLE = Role.COORDINATOR


class AccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        if not user.role:
            user.role = DEFAULT_SIGNUP_ROLE
        if commit:
            user.save()
        return user


class SocialAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        if not user.role:
            user.role = DEFAULT_SIGNUP_ROLE
            user.save(update_fields=["role"])
        return user
