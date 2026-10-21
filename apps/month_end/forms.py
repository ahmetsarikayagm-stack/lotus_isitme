from decimal import Decimal

from django import forms

from apps.core.forms import TailwindFormMixin

from .models import MonthEnd

MONEY = {"min": "0", "placeholder": "0.00"}


class MonthEndForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = MonthEnd
        fields = ["year", "month", "rent", "electricity", "water", "internet", "salary", "accounting", "general_expenses"]
        widgets = {
            "year": forms.NumberInput(attrs={"min": "2000", "max": "2100"}),
            **{f: forms.NumberInput(attrs=MONEY) for f in MonthEnd.FIXED_EXPENSE_FIELDS},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in MonthEnd.FIXED_EXPENSE_FIELDS:  # boş bırakılan gider = 0
            self.fields[name].required = False
        if self.instance.pk and self.instance.is_closed:  # kapalı ay: tüm alanlar salt okunur
            for field in self.fields.values():
                field.disabled = True

    def clean(self):
        cleaned = super().clean()
        for name in MonthEnd.FIXED_EXPENSE_FIELDS:
            if cleaned.get(name) is None and name not in self.errors:
                cleaned[name] = Decimal("0")
        return cleaned
