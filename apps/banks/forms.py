from django import forms

from apps.core.forms import TailwindFormMixin

from .models import Bank


class BankForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Bank
        fields = ["payment_method", "name"]
        widgets = {"name": forms.TextInput(attrs={"placeholder": "Örn. Ziraat Bankası"})}
