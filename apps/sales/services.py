"""Satış iş kuralları: kalemler, stok düşme/iade, toplamlar ve ay sonu güncelleme."""
from collections import defaultdict

from django.db import transaction
from django.db.models import F

from apps.core.crud import CrudError
from apps.month_end.models import MONTHS, MonthEnd
from apps.stocks.models import Stock

from .models import Sale, SaleItem


def _refresh_periods(*dates):
    for y, m in {(d.year, d.month) for d in dates if d}:
        MonthEnd.refresh(y, m)


def _ensure_open(*dates):
    """Kapatılmış bir aya ait satış eklenemez, değiştirilemez, silinemez."""
    names = dict(MONTHS)
    for y, m in sorted({(d.year, d.month) for d in dates if d}):
        if MonthEnd.is_period_closed(y, m):
            raise CrudError(
                f"{names[m]} {y} ayı kapatılmış; bu tarihteki satışlar değiştirilemez. "
                "Gerekirse Admin, Ay Sonu sayfasından ayı yeniden açabilir."
            )


def _restore_stock(items):
    """Kalemlerin adetlerini ürün bazında stoğa iade eder."""
    per_product = defaultdict(int)
    for product_id, qty in items:
        per_product[product_id] += qty
    for product_id, qty in per_product.items():
        Stock.all_objects.filter(pk=product_id).update(quantity=F("quantity") + qty)


@transaction.atomic
def save_sale(sale: Sale, items: list[dict]) -> Sale:
    """
    Satışı ve kalemlerini kaydeder.

    items: [{"id", "category", "product", "quantity", "unit_price",
             "institution_right", "warranty_end", "product_life"}, ...]  (silinenler listede yoktur)

    Düzenlemede önce eski kalemlerin adetleri stoğa iade edilir, sonra yeni kalemler düşülür;
    böylece ekleme / çıkarma / adet ve ürün değişikliği tek mantıkla doğru sonuçlanır.
    """
    if not items:
        raise CrudError("En az bir ürün kalemi eklemelisiniz.")

    old_items, old_date = [], None
    if sale.pk:
        old_date = Sale.all_objects.values_list("sale_date", flat=True).get(pk=sale.pk)  # DB'deki eski tarih
    _ensure_open(sale.sale_date, old_date)  # hiçbir değişiklik yapmadan önce kontrol et
    if sale.pk:
        old_items = list(SaleItem.objects.select_for_update().filter(sale_id=sale.pk))
        _restore_stock((i.product_id, i.quantity) for i in old_items)

    need = defaultdict(int)
    for d in items:
        need[d["product"].pk] += d["quantity"]
    stocks = {s.pk: s for s in Stock.all_objects.select_for_update().filter(pk__in=need)}
    for pid, qty in need.items():
        if qty > stocks[pid].quantity:
            raise CrudError(f"Yetersiz stok: {stocks[pid]} için mevcut adet {stocks[pid].quantity}, istenen {qty}.")
    for pid, qty in need.items():
        Stock.all_objects.filter(pk=pid).update(quantity=F("quantity") - qty)

    sale.save()  # başlık (yeni satışta pk burada oluşur)

    old_by_id = {i.pk: i for i in old_items}
    keep_ids = {d["id"] for d in items if d.get("id") in old_by_id}
    SaleItem.objects.filter(pk__in=[i.pk for i in old_items if i.pk not in keep_ids]).delete()

    for d in items:
        stock = stocks[d["product"].pk]
        item = old_by_id.get(d.get("id"))
        if item is None:
            item = SaleItem(sale=sale, unit_cost=stock.price)
        elif item.product_id != stock.pk:
            item.unit_cost = stock.price  # ürün değiştiyse maliyet yeni ürüne göre; aynıysa satış anındaki maliyet korunur
        item.category = d["category"]
        item.product = stock
        item.quantity = d["quantity"]
        item.unit_price = d["unit_price"]
        item.institution_right = d.get("institution_right", False)
        item.warranty_end = d.get("warranty_end")
        item.product_life = d.get("product_life")
        item.save()

    sale.recalculate()
    sale.save(update_fields=["total", "remaining"])
    _refresh_periods(sale.sale_date, old_date)
    return sale


@transaction.atomic
def delete_sale(sale: Sale) -> None:
    """Satışı (soft) siler ve tüm kalemlerin adedini stoğa geri ekler."""
    _ensure_open(sale.sale_date)
    _restore_stock(SaleItem.objects.filter(sale_id=sale.pk).values_list("product_id", "quantity"))
    sale.delete()
    _refresh_periods(sale.sale_date)
