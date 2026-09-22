"""Login by ID number / phone / email / username — so people with the same name
can still sign in uniquely with their own ID."""
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class MultiIdentifierBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or password is None:
            return None
        User = get_user_model()
        ident = username.strip()
        try:
            user = User.objects.get(
                Q(username__iexact=ident) | Q(email__iexact=ident)
                | Q(id_number__iexact=ident) | Q(phone__iexact=ident))
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
