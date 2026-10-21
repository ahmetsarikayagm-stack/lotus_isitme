"""Dashboard için KPI ve grafik verileri."""
from datetime import date

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from apps.month_end.models import MonthEnd
from apps.patients.models import Patient
from apps.sales.models import Sale, SaleItem
from apps.stocks.models import LOW_STOCK_THRESHOLD, Stock

MONTH_SHORT = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
MONEY = DecimalField(max_digits=16, decimal_places=2)


def tl(value) -> str:
    return f"{float(value or 0):,.0f}".replace(",", ".") + " ₺"


def last_months(today: date, n: int = 12) -> list[tuple[int, int]]:
    y, m, out = today.year, today.month, []
    for _ in range(n):
        out.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return out[::-1]


def get_dashboard_data() -> dict:
    today = timezone.localdate()
    months = last_months(today)
    first = date(months[0][0], months[0][1], 1)
    labels = [f"{MONTH_SHORT[m - 1]} {str(y)[2:]}" for y, m in months]

    # --- KPI
    this_month = Sale.objects.filter(sale_date__year=today.year, sale_date__month=today.month).aggregate(
        revenue=Sum("total"), count=Count("pk"))
    month_units = SaleItem.objects.alive().filter(
        sale__sale_date__year=today.year, sale__sale_date__month=today.month).aggregate(u=Sum("quantity"))["u"]
    receivable = Sale.objects.aggregate(total=Sum("remaining"))["total"]
    stock = Stock.objects.aggregate(
        units=Sum("quantity"),
        value=Sum(ExpressionWrapper(F("price") * F("quantity"), output_field=MONEY)),
        low=Count("pk", filter=Q(quantity__lte=LOW_STOCK_THRESHOLD)),
    )
    month_end = MonthEnd.objects.filter(year=today.year, month=today.month).first()

    kpis = [
        {"label": "Toplam Hasta", "value": f"{Patient.objects.count():,}".replace(",", "."), "hint": "Kayıtlı hasta", "icon": "users", "tone": "brand"},
        {"label": "Bu Ay Ciro", "value": tl(this_month["revenue"]),
         "hint": f"{this_month['count'] or 0} satış · {month_units or 0} adet", "icon": "shopping-cart", "tone": "emerald"},
        {"label": "Stok Değeri", "value": tl(stock["value"]),
         "hint": f"{stock['units'] or 0} adet · {stock['low'] or 0} kalem azalıyor", "icon": "archive-box", "tone": "sky"},
        {"label": "Kalan Alacak", "value": tl(receivable), "hint": "Tahsil edilmemiş bakiye", "icon": "credit-card", "tone": "amber"},
        {"label": "Bu Ay Kâr / Zarar", "value": tl(month_end.profit) if month_end else "—",
         "hint": "Ay sonu kaydına göre" if month_end else "Bu ay için ay sonu girilmemiş",
         "icon": "chart-bar", "tone": "rose" if month_end and month_end.profit < 0 else "violet"},
    ]

    # --- Grafikler
    revenue_by_month = {
        (d.year, d.month): float(rev or 0)
        for d, rev in Sale.objects.filter(sale_date__gte=first).annotate(m=TruncMonth("sale_date"))
        .values("m").annotate(rev=Sum("total")).order_by().values_list("m", "rev")
    }
    units_by_month = {
        (d.year, d.month): qty or 0
        for d, qty in SaleItem.objects.alive().filter(sale__sale_date__gte=first)
        .annotate(m=TruncMonth("sale__sale_date")).values("m").annotate(qty=Sum("quantity"))
        .order_by().values_list("m", "qty")
    }
    payments = (Sale.objects.filter(sale_date__gte=first).values("payment_method__name")
                .annotate(total=Sum("total")).order_by("-total"))
    brands = (SaleItem.objects.alive().filter(sale__sale_date__gte=first).values("product__brand__name")
              .annotate(qty=Sum("quantity")).order_by("-qty")[:6])
    ends = {(e.year, e.month): e for e in MonthEnd.objects.filter(year__gte=months[0][0])}

    charts = {
        "revenue": {"labels": labels, "values": [revenue_by_month.get(k, 0) for k in months],
                    "units": [units_by_month.get(k, 0) for k in months]},
        "payments": {"labels": [p["payment_method__name"] for p in payments],
                     "values": [float(p["total"] or 0) for p in payments]},
        "brands": {"labels": [b["product__brand__name"] for b in brands], "values": [b["qty"] or 0 for b in brands]},
        "profit": {
            "labels": labels,
            "expense": [float(ends[k].total_expense) if k in ends else 0 for k in months],
            "profit": [float(ends[k].profit) if k in ends else 0 for k in months],
        },
    }

    return {
        "kpis": kpis,
        "charts": charts,
        "recent_sales": Sale.objects.select_related("patient")
        .prefetch_related("items__product__brand", "items__product__model").order_by("-sale_date", "-pk")[:6],
        "low_stock": Stock.objects.filter(quantity__lte=LOW_STOCK_THRESHOLD).select_related("brand", "model")
        .order_by("quantity", "brand__name")[:6],
    }
