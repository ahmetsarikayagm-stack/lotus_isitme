from collections import defaultdict

from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory

from apps.banks.models import Bank
from apps.core.forms import CascadeSelect, TailwindFormMixin
from apps.patients.models import Patient

from .models import Sale, SaleItem

MAX_FILE_MB = 25


class SaleForm(TailwindFormMixin, forms.ModelForm):
    """Satış başlığı (hasta, ödeme, kapora, dosyalar). Ürünler SaleItemFormSet'te."""

    class Meta:
        model = Sale
        fields = ["patient", "sale_date", "payment_method", "bank", "discount", "deposit", "audio_file", "report_file", "notes"]
        widgets = {
            "bank": CascadeSelect("id_payment_method"),
            "discount": forms.NumberInput(attrs={"min": "0", "placeholder": "0.00"}),
            "deposit": forms.NumberInput(attrs={"min": "0", "placeholder": "0.00"}),
            "notes": forms.Textarea(attrs={"rows": 4, "placeholder": "Satışla ilgili notlar..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        f = self.fields
        f["patient"].queryset = Patient.objects.order_by("full_name")
        f["patient"].label_from_instance = lambda p: f"{p.full_name} · {p.tc_no}"
        f["patient"].widget.attrs["data-filterable"] = "Hasta ara (ad veya T.C.)"

        banks = Bank.objects.order_by("name")
        f["bank"].queryset = banks
        f["bank"].widget.parent_map = {str(b.pk): b.payment_method_id for b in banks}
        f["bank"].help_text = "Nakit gibi bankasız ödemelerde boş bırakın."
        f["discount"].help_text = "Tüm sepete uygulanan toplam indirim."
        f["audio_file"].help_text = f"PDF, görsel veya ses dosyası (en fazla {MAX_FILE_MB} MB)."
        f["report_file"].help_text = f"PDF, görsel veya Word dosyası (en fazla {MAX_FILE_MB} MB)."

    def _check_size(self, name):
        file = self.cleaned_data.get(name)
        if file and hasattr(file, "size") and file.size > MAX_FILE_MB * 1024 * 1024:
            raise forms.ValidationError(f"Dosya en fazla {MAX_FILE_MB} MB olabilir.")
        return file

    def clean_audio_file(self):
        return self._check_size("audio_file")

    def clean_report_file(self):
        return self._check_size("report_file")


class SaleItemForm(TailwindFormMixin, forms.ModelForm):
    """Sepetteki tek satır. Ürün listesi, satırın kendi kategorisine göre süzülür."""

    class Meta:
        model = SaleItem
        fields = ["category", "product", "quantity", "unit_price", "institution_right", "warranty_end", "product_life"]
        widgets = {
            "product": CascadeSelect("id_category"),
            "quantity": forms.NumberInput(attrs={"min": "1"}),
            "unit_price": forms.NumberInput(attrs={"min": "0", "placeholder": "0.00"}),
            "product_life": forms.NumberInput(attrs={"min": "0", "placeholder": "Örn. 5"}),
        }

    def __init__(self, *args, stocks=None, stock_choices=None, stock_map=None, category_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        product = self.fields["product"]
        if stocks is not None:
            product.queryset = stocks  # doğrulama için
        if stock_choices is not None:
            product.widget.choices = stock_choices  # tüm satırlar aynı listeyi kullanır (ek sorgu yok)
        product.widget.parent_map = stock_map or {}
        product.widget.attrs["data-cascade-parent"] = f"id_{self.add_prefix('category')}"
        if category_choices is not None:
            self.fields["category"].widget.choices = category_choices
        self.fields["institution_right"].label = "SGK (kurum hakkı)"


class BaseSaleItemFormSet(BaseInlineFormSet):
    default_error_messages = {"too_few_forms": "En az bir ürün kalemi eklemelisiniz."}

    def add_fields(self, form, index):
        super().add_fields(form, index)
        if "DELETE" in form.fields:
            form.fields["DELETE"].widget.attrs["x-ref"] = "del"  # satır "Sil" butonu bu kutuyu işaretler

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        # Stok kontrolü: aynı ürün birden fazla satırda olabilir, toplam istenen adet stoğu aşmamalı
        need, rows = defaultdict(int), defaultdict(list)
        for f in self.forms:
            cd = getattr(f, "cleaned_data", None)
            if not cd or cd.get("DELETE") or not cd.get("product"):
                continue
            need[cd["product"].pk] += cd["quantity"]
            rows[cd["product"].pk].append(f)
        returned = defaultdict(int)  # düzenlemede bu satışın eski adetleri stoğa iade edilecek
        if self.instance.pk:
            for pid, qty in SaleItem.objects.filter(sale_id=self.instance.pk).values_list("product_id", "quantity"):
                returned[pid] += qty
        for pid, qty in need.items():
            available = rows[pid][0].cleaned_data["product"].quantity + returned.get(pid, 0)
            if qty > available:
                rows[pid][-1].add_error("quantity", f"Yetersiz stok. Mevcut adet: {available}")


SaleItemFormSet = inlineformset_factory(
    Sale, SaleItem, form=SaleItemForm, formset=BaseSaleItemFormSet,
    extra=0, min_num=1, validate_min=True, can_delete=True,
)
