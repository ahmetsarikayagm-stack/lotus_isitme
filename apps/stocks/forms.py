from django import forms

from apps.brands.models import Brand
from apps.core.forms import CascadeSelect, TailwindFormMixin
from apps.models_app.models import DeviceModel

from .models import Stock

MAX_IMAGE_MB = 5


class StockForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Stock
        fields = ["category", "brand", "model", "price", "quantity", "image", "description"]
        widgets = {
            "brand": CascadeSelect("id_category"),
            "model": CascadeSelect("id_brand"),
            "price": forms.NumberInput(attrs={"min": "0", "placeholder": "0.00"}),
            "quantity": forms.NumberInput(attrs={"min": "0"}),
            "description": forms.Textarea(attrs={"rows": 4, "placeholder": "Ürün özellikleri, seri no, notlar..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        brands = Brand.objects.order_by("name")
        models = DeviceModel.objects.order_by("name")
        self.fields["brand"].queryset = brands
        self.fields["brand"].widget.parent_map = {str(b.pk): b.category_id for b in brands}
        self.fields["model"].queryset = models
        self.fields["model"].widget.parent_map = {str(m.pk): m.brand_id for m in models}
        self.fields["image"].help_text = f"JPG / PNG, en fazla {MAX_IMAGE_MB} MB."

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and hasattr(image, "size") and image.size > MAX_IMAGE_MB * 1024 * 1024:
            raise forms.ValidationError(f"Görsel en fazla {MAX_IMAGE_MB} MB olabilir.")
        return image
