from decimal import Decimal

from django.db.models import Q

from apps.categories.models import Category
from apps.core.crud import Card, Col, CrudConfig, Filter, choices_from
from apps.payments.models import PaymentMethod
from apps.stocks.models import Stock

from . import services
from .forms import SaleForm, SaleItemFormSet
from .models import Sale, SaleItem


class SaleCrud(CrudConfig):
    model = Sale
    form_class = SaleForm
    formset_class = SaleItemFormSet
    module_key = "sales"
    namespace = "sales"
    singular = "Satış"
    plural = "Satışlar"
    form_template = "sales/form.html"
    search_placeholder = "Hasta, T.C., ürün veya not ara..."
    search_fields = ("patient__full_name", "patient__tc_no", "items__product__brand__name", "items__product__model__name", "notes")
    ordering = ("-sale_date", "-pk")
    columns = (
        Col("Tarih", "sale_date", "sale_date", kind="date"),
        Col("Hasta", "patient.full_name", "patient__full_name", link=True),
        Col("Ürünler", "items_summary"),
        Col("Toplam", "total", "total", kind="money"),
        Col("Kapora", "deposit", "deposit", kind="money"),
        Col("Kalan", "remaining", "remaining", kind="money"),
        Col("Ödeme", "payment_method.name", "payment_method__name"),
        Col("SGK", "has_institution", kind="bool"),
        Col("Odyo", "audio_file", kind="file"),
        Col("Rapor", "report_file", kind="file"),
        Col("Kaydeden", "created_by.display_name", "created_by__first_name"),
        Col("Son İşlem", "last_action_text", "updated_at"),
    )
    filters = (
        Filter("odeme", "Ödeme", "payment_method_id", choices_from(PaymentMethod)),
        Filter("kategori", "Kategori", "items__category_id", choices_from(Category)),
        Filter("sgk", "SGK", "items__institution_right", lambda: [("true", "SGK'lı kalem içerenler")]),
        Filter("bakiye", "Bakiye", "remaining__gt", lambda: [("0", "Kalan borcu olanlar")]),
        Filter("bas", "Başlangıç", "sale_date__gte", kind="date"),
        Filter("bit", "Bitiş", "sale_date__lte", kind="date"),
    )

    @classmethod
    def get_queryset(cls, request):
        return (Sale.objects.select_related("patient", "payment_method", "created_by", "updated_by")
                .prefetch_related("items__product__brand", "items__product__model")
                .distinct())  # kalem üzerinden arama/filtre aynı satışı tekrarlamasın

    # --- satır (sepet) formu için ürün listesi: tek sorgu, tüm satırlar paylaşır
    @staticmethod
    def _stock_queryset(obj):
        """Satılabilir stok: silinmemiş ve adedi > 0; düzenlemede mevcut kalemlerin ürünleri her zaman dahil."""
        available = Q(is_deleted=False, quantity__gt=0)
        if obj is not None and obj.pk:
            available |= Q(pk__in=SaleItem.objects.filter(sale_id=obj.pk).values("product_id"))
        return Stock.all_objects.filter(available).select_related("brand", "model").order_by("brand__name", "model__name")

    @classmethod
    def form_context(cls, request, obj):
        """Sepet satırındaki ürün küçük resmi için: ürün resmi, yoksa marka logosu, yoksa boş."""
        images = {
            str(s.pk): {
                "image": s.image.url if s.image else "",
                "logo": s.brand.logo.url if s.brand.logo else "",
                "name": f"{s.brand} {s.model}",
            }
            for s in cls._stock_queryset(obj)
        }
        return {"product_images": images}

    @classmethod
    def formset_kwargs(cls, request, obj):
        stocks = cls._stock_queryset(obj)
        stock_list = list(stocks)
        return {"form_kwargs": {
            "stocks": stocks,
            "stock_choices": [("", "---------")] + [(s.pk, f"{s.brand} {s.model} · Stok: {s.quantity}") for s in stock_list],
            "stock_map": {str(s.pk): s.category_id for s in stock_list},
            "category_choices": [("", "---------")] + [(c.pk, c.name) for c in Category.objects.all()],
        }}

    @classmethod
    def cross_validate(cls, form, formset):
        subtotal = Decimal("0")
        for f in formset.forms:
            cd = getattr(f, "cleaned_data", None)
            if cd and not cd.get("DELETE") and cd.get("product"):
                subtotal += cd["unit_price"] * cd["quantity"]
        discount = form.cleaned_data.get("discount") or Decimal("0")
        deposit = form.cleaned_data.get("deposit") or Decimal("0")
        if discount > subtotal:
            form.add_error("discount", "İndirim ürün toplamından büyük olamaz.")
        elif deposit > subtotal - discount:
            form.add_error("deposit", "Kapora toplam tutardan büyük olamaz.")

    @classmethod
    def save_object(cls, request, form, obj, creating, formset=None):
        items = []
        for f in formset.forms:
            cd = getattr(f, "cleaned_data", None)
            if not cd or cd.get("DELETE") or not cd.get("product"):
                continue  # boş veya silinmiş satır
            items.append({
                "id": cd["id"].pk if cd.get("id") else None,
                "category": cd["category"], "product": cd["product"],
                "quantity": cd["quantity"], "unit_price": cd["unit_price"],
                "institution_right": cd.get("institution_right", False),
                "warranty_end": cd.get("warranty_end"), "product_life": cd.get("product_life"),
            })
        services.save_sale(obj, items)
        form.save_m2m()

    @classmethod
    def delete_object(cls, request, obj):
        services.delete_sale(obj)
