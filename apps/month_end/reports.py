"""Rapor veri katmanı: PDF ve Excel üreticileri aynı veriyi kullanır."""
from pathlib import Path

from django.conf import settings

from apps.core.company import company_info  # noqa: F401  (raporlar buradan içe aktarır)
from apps.sales.models import Sale, SaleItem

from .models import MONTHS, MonthEnd
from .services import EXPENSE_LABELS, month_summary

LOGO_WHITE = Path(settings.BASE_DIR) / "static" / "img" / "logo-white.png"
PDF_MIME = "application/pdf"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def month_report_data(me: MonthEnd) -> dict:
    sales = list(
        Sale.objects.filter(sale_date__year=me.year, sale_date__month=me.month)
        .select_related("patient", "payment_method", "bank")
        .prefetch_related("items__product__brand", "items__product__model")
        .order_by("sale_date", "pk")
    )
    items = list(
        SaleItem.objects.alive().filter(sale__sale_date__year=me.year, sale__sale_date__month=me.month)
        .select_related("sale__patient", "category", "product__brand", "product__model")
        .order_by("sale__sale_date", "sale_id", "pk")
    )
    return {
        "me": me,
        "summary": month_summary(me),
        "expenses": [(label, getattr(me, field)) for field, label in EXPENSE_LABELS.items()],
        "sales": sales,
        "items": items,
    }


def year_report_data(year: int) -> dict:
    records = {m.month: m for m in MonthEnd.objects.filter(year=year)}
    return {"year": year, "rows": [{"month": n, "name": name, "obj": records.get(n)} for n, name in MONTHS]}
