from django.utils import timezone

from apps.core.crud import Card, Col, CrudConfig, CrudError, Filter, RowAction

from .forms import MonthEndForm
from .models import MONTHS, MonthEnd
from .services import month_summary


def _years():
    return [(str(y), str(y)) for y in MonthEnd.objects.order_by("-year").values_list("year", flat=True).distinct()]


class MonthEndCrud(CrudConfig):
    model = MonthEnd
    form_class = MonthEndForm
    module_key = "month_end"
    namespace = "month_end"
    singular = "Ay Sonu"
    plural = "Ay Sonu"
    form_template = "month_end/form.html"
    list_template = "month_end/list.html"
    search_placeholder = "Yıl ara..."
    search_fields = ("year",)
    ordering = ("-year", "-month")
    columns = (
        Col("Dönem", "period_label", link=True),
        Col("Toplam Gelir", "total_income", "total_income", kind="money"),
        Col("Cihaz Maliyeti", "device_cost", "device_cost", kind="money"),
        Col("Sabit Giderler", "fixed_expenses", kind="money"),
        Col("Toplam Gider", "total_expense", "total_expense", kind="money"),
        Col("Kâr / Zarar", "profit", "profit", kind="profit"),
        Col("Durum", "is_closed", "is_closed", kind="status"),
    )
    filters = (
        Filter("yil", "Yıl", "year", _years),
        Filter("ay", "Ay", "month", lambda: [(str(n), name) for n, name in MONTHS]),
        Filter("durum", "Durum", "is_closed", lambda: [("true", "Kapalı"), ("false", "Açık")]),
    )
    row_actions = (
        RowAction("PDF", "report_pdf", title="PDF rapor", tone="red", new_tab=True),
        RowAction("Excel", "report_xlsx", title="Excel rapor", tone="green"),
    )
    cards = (
        Card("Dönem", ("year", "month"), "Gelir ve cihaz maliyeti seçilen aydaki satışlardan otomatik hesaplanır."),
        Card("Sabit Giderler", ("rent", "electricity", "water", "internet", "salary", "accounting", "general_expenses")),
    )

    @classmethod
    def initial(cls, request):
        today = timezone.localdate()
        return {"year": today.year, "month": today.month}

    @classmethod
    def form_context(cls, request, obj):
        if obj is not None and obj.pk:
            return {"summary": month_summary(obj)}
        # Yeni kayıt: en son kaydın giderlerini tek tıkla getirmek için
        last = MonthEnd.objects.order_by("-year", "-month").first()
        if last is None:
            return {}
        return {"copy_source": {
            "label": last.period_label,
            "values": {f: float(getattr(last, f)) for f in MonthEnd.FIXED_EXPENSE_FIELDS},
        }}

    @classmethod
    def save_object(cls, request, form, obj, creating, formset=None):
        if obj.pk and MonthEnd.objects.filter(pk=obj.pk, is_closed=True).exists():
            raise CrudError("Kapatılmış ay düzenlenemez. Önce Admin'in ayı yeniden açması gerekir.")
        super().save_object(request, form, obj, creating, formset)

    @classmethod
    def delete_object(cls, request, obj):
        if obj.is_closed:
            raise CrudError("Kapatılmış ay silinemez. Önce ayı yeniden açın.")
        obj.delete()

    @classmethod
    def list_context(cls, request):
        """Yıllık rapor düğmesi için yıl: filtredeki yıl, yoksa en son kayıtlı yıl, yoksa bu yıl."""
        try:
            year = int(request.GET.get("yil", ""))
        except ValueError:
            year = None
        year = year or MonthEnd.objects.order_by("-year").values_list("year", flat=True).first() or timezone.localdate().year
        return {"report_year": year}
