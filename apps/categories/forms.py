from django import forms

from apps.core.forms import TailwindFormMixin

from .models import Category


class CategoryForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name"]
        widgets = {"name": forms.TextInput(attrs={"placeholder": "Örn. İşitme Cihazı", "autofocus": True})}
