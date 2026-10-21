"""Ay Sonu analizleri: karşılaştırma, tahsilat, satış kırılımı, günlük seri."""
from calendar import monthrange
from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.urls import reverse

from apps.sales.models import Sale, SaleItem

from .models import MONTHS, MonthEnd

ZERO = Decimal("0")
MONEY = DecimalField(max_digits=16, decimal_places=2)
LINE_TOTAL = ExpressionWrapper(F("unit_price") * F("quantity"), output_field=MONEY)
EXPENSE_LABELS = {
    "rent": "Kira", "electricity": "Elektrik", "water": "Su", "internet": "İnternet",
    "salary": "Maaş", "accounting": "Muhasebe", "general_expenses": "Genel Giderler",
}
MONTH_NAMES = dict(MONTHS)


def tl(value) -> str:
    """1234.5 -> '1.234,50 ₺'"""
    s = f"{float(value or 0):,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".") + " ₺"


def _margin(profit, income):
    return float(profit / income * 100) if income else None


def _snapshot(obj):
    if obj is None:
        return None
    return {
        "label": obj.period_label,
        "income": float(obj.total_income),
        "expense": float(obj.total_expense),
        "profit": float(obj.profit),
        "margin": _margin(obj.profit, obj.total_income),
    }


def _shares(rows, key):
    """Satırlara toplamdaki pay yüzdesini (pct) ekler."""
    total = sum(float(r[key] or 0) for r in rows) or 1
    for r in rows:
        r["pct"] = round(float(r[key] or 0) / total * 100)
    return rows


def month_summary(me: MonthEnd) -> dict:
    y, m = me.year, me.month
    sales = Sale.objects.filter(sale_date__year=y, sale_date__month=m)
    items = SaleItem.objects.alive().filter(sale__sale_date__year=y, sale__sale_date__month=m)

    agg = sales.aggregate(count=Count("pk"), income=Sum("total"), collected=Sum("deposit"),
                          receivable=Sum("remaining"), discount=Sum("discount"))
    item_agg = items.aggregate(units=Sum("quantity"), all_income=Sum(LINE_TOTAL),
                               sgk_income=Sum(LINE_TOTAL, filter=Q(institution_right=True)))
    count, income = agg["count"] or 0, agg["income"] or ZERO
    collected, receivable = agg["collected"] or ZERO, agg["receivable"] or ZERO
    sgk_income = item_agg["sgk_income"] or ZERO
    other_income = (item_agg["all_income"] or ZERO) - sgk_income
    sgk_sales = sales.filter(pk__in=items.filter(institution_right=True).values("sale_id")).count()

    payments = _shares(list(
        sales.values("payment_method__name").annotate(total=Sum("total"), n=Count("pk")).order_by("-total")
    ), "total")
    brands = _shares(list(
        items.values("product__brand__name").annotate(units=Sum("quantity"), total=Sum(LINE_TOTAL)).order_by("-units")
    ), "units")

    days = monthrange(y, m)[1]

    # --- karşılaştırma
    py, pm = (y, m - 1) if m > 1 else (y - 1, 12)
    prev_month = _snapshot(MonthEnd.objects.filter(year=py, month=pm).first())
    prev_year = _snapshot(MonthEnd.objects.filter(year=y - 1, month=m).first())

    margin = _margin(me.profit, me.total_income)
    sales_url = f"{reverse('sales:list')}?bas={y}-{m:02d}-01&bit={y}-{m:02d}-{days:02d}"

    kpis = [
        {"key": "income", "label": "Toplam Gelir", "text": tl(me.total_income)},
        {"key": "expense", "label": "Toplam Gider", "text": tl(me.total_expense)},
        {"key": "profit", "label": "Net Kâr / Zarar", "text": tl(me.profit), "negative": me.profit < 0},
        {"key": "margin", "label": "Kâr Marjı", "text": "—" if margin is None else f"%{margin:.1f}".replace(".", ",")},
    ]

    return {
        "kpis": kpis,
        "period": me.period_label,
        "income": me.total_income, "device_cost": me.device_cost,
        "collected": collected, "receivable": receivable,
        "collected_text": tl(collected), "receivable_text": tl(receivable), "device_cost_text": tl(me.device_cost),
        "collect_pct": round(float(collected / income * 100)) if income else 0,
        "count": count, "units": item_agg["units"] or 0,
        "avg_ticket_text": tl(income / count) if count else "—",
        "sgk_count": sgk_sales, "sgk_income_text": tl(sgk_income),
        "other_income_text": tl(other_income), "discount_text": tl(agg["discount"]),
        "avg_ticket": income / count if count else ZERO, "sgk_income": sgk_income,
        "other_income": other_income, "discount": agg["discount"] or ZERO,
        "margin": margin,
        "payments": payments, "brands": brands,
        "sales_url": sales_url,
        "prev_month_label": f"{MONTH_NAMES[pm]} {py}", "prev_year_label": f"{MONTH_NAMES[m]} {y - 1}",
        "has_prev_month": prev_month is not None, "has_prev_year": prev_year is not None,
        "chart_data": {
            "income": float(me.total_income),
            "deviceCost": float(me.device_cost),
            "expenseFields": list(EXPENSE_LABELS.keys()),
            "prevMonth": prev_month, "prevYear": prev_year,
        },
    }
