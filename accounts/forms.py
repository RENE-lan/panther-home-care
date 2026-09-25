"""Custom signup — capture (and show) the login ID number + phone at registration."""
import random

from django import forms
from django.contrib import messages

from .models import User


class PantherSignupForm(forms.Form):
    id_number = forms.CharField(
        label="Numéro d'identification (optionnel)", required=False, max_length=40,
        widget=forms.TextInput(attrs={"placeholder": "Laissez vide pour en générer un"}))
    phone = forms.CharField(
        label="Téléphone", required=False, max_length=32,
        widget=forms.TextInput(attrs={"placeholder": "+243 …"}))

    field_order = ["email", "username", "id_number", "phone", "password1", "password2"]

    def clean_id_number(self):
        idn = (self.cleaned_data.get("id_number") or "").strip()
        if idn and User.objects.filter(id_number__iexact=idn).exists():
            raise forms.ValidationError("Ce numéro d'identification est déjà utilisé.")
        return idn

    def signup(self, request, user):
        idn = (self.cleaned_data.get("id_number") or "").strip()
        if not idn:
            while True:
                cand = f"ID-{random.randint(10000, 99999)}"
                if not User.objects.filter(id_number=cand).exists():
                    idn = cand
                    break
        user.id_number = idn
        user.phone = (self.cleaned_data.get("phone") or "").strip()
        user.save(update_fields=["id_number", "phone"])
        messages.success(
            request, f"Compte créé. Votre numéro d'identification est {idn} — "
                     "utilisez-le pour vous connecter.")
