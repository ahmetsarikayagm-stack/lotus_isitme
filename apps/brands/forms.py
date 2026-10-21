from django import forms

from apps.core.forms import TailwindFormMixin

from .models import Brand

MAX_LOGO_MB = 2


class BrandForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Brand
        fields = ["category", "name", "logo"]
        widgets = {"name": forms.TextInput(attrs={"placeholder": "Örn. Phonak"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["logo"].help_text = f"PNG, JPG veya WebP; şeffaf zeminli PNG en iyisidir (en fazla {MAX_LOGO_MB} MB)."

    def clean_logo(self):
        logo = self.cleaned_data.get("logo")
        if logo and hasattr(logo, "size") and logo.size > MAX_LOGO_MB * 1024 * 1024:
            raise forms.ValidationError(f"Logo en fazla {MAX_LOGO_MB} MB olabilir.")
        return logo
