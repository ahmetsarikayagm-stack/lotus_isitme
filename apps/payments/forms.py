from django import forms

from apps.core.forms import TailwindFormMixin

from .models import PaymentMethod


class PaymentMethodForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = PaymentMethod
        fields = ["name"]
        widgets = {"name": forms.TextInput(attrs={"placeholder": "Örn. Kredi Kartı", "autofocus": True})}
