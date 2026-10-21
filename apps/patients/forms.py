from django import forms

from apps.core.forms import TailwindFormMixin

from .models import Patient


class PatientForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Patient
        fields = ["full_name", "tc_no", "phone", "phone2", "address", "notes"]
        widgets = {
            "full_name": forms.TextInput(attrs={"placeholder": "Ad Soyad", "autofocus": True}),
            "tc_no": forms.TextInput(attrs={"placeholder": "11 haneli T.C. kimlik no", "maxlength": 11,
                                            "inputmode": "numeric", "autocomplete": "off"}),
            "phone": forms.TextInput(attrs={"placeholder": "05XX XXX XX XX", "inputmode": "tel"}),
            "phone2": forms.TextInput(attrs={"placeholder": "İsteğe bağlı", "inputmode": "tel"}),
            "address": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 4, "placeholder": "Hasta ile ilgili özel notlar..."}),
        }

    def clean_tc_no(self):
        tc = self.cleaned_data["tc_no"].strip()
        if Patient.objects.filter(tc_no=tc).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Bu T.C. kimlik numarasıyla kayıtlı bir hasta zaten var.")
        return tc
