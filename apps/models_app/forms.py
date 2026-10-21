from django import forms

from apps.brands.models import Brand
from apps.core.forms import TailwindFormMixin

from .models import DeviceModel


class DeviceModelForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = DeviceModel
        fields = ["brand", "name"]
        widgets = {"name": forms.TextInput(attrs={"placeholder": "Örn. Audéo Lumity L90"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["brand"].queryset = Brand.objects.select_related("category").order_by("category__name", "name")
        self.fields["brand"].label_from_instance = lambda b: f"{b.name}  ({b.category.name})"
