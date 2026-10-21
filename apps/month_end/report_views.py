from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from apps.accounts.mixins import AdminRequiredMixin, ModuleAccessMixin

from .models import MonthEnd
from .report_pdf import build_month_pdf, build_year_pdf
from .report_xlsx import build_month_xlsx, build_year_xlsx
from .reports import PDF_MIME, XLSX_MIME, month_report_data, year_report_data


def _response(content: bytes, fmt: str, filename: str) -> HttpResponse:
    if fmt == "pdf":
        resp = HttpResponse(content, content_type=PDF_MIME)
        resp["Content-Disposition"] = f'inline; filename="{filename}.pdf"'   # tarayıcıda açılır, indirilebilir/yazdırılabilir
    else:
        resp = HttpResponse(content, content_type=XLSX_MIME)
        resp["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
    resp["Cache-Control"] = "no-store"
    return resp


class MonthReportView(ModuleAccessMixin, View):
    module_key = "month_end"
    fmt = "pdf"

    def get(self, request, pk):
        me = get_object_or_404(MonthEnd, pk=pk)
        data = month_report_data(me)
        who = request.user.display_name
        builder = build_month_pdf if self.fmt == "pdf" else build_month_xlsx
        return _response(builder(data, who), self.fmt, f"Lotus_AySonu_{me.year}-{me.month:02d}")


class YearReportView(ModuleAccessMixin, View):
    module_key = "month_end"
    fmt = "pdf"

    def get(self, request, year):
        if not 2000 <= year <= 2100:
            raise Http404
        data = year_report_data(year)
        who = request.user.display_name
        builder = build_year_pdf if self.fmt == "pdf" else build_year_xlsx
        return _response(builder(data, who), self.fmt, f"Lotus_AySonu_Yillik_{year}")


class MonthCloseView(ModuleAccessMixin, View):
    """Ayı kapatır: değerler dondurulur, o aya ait satışlar değiştirilemez."""
    module_key = "month_end"
    http_method_names = ["post"]

    def post(self, request, pk):
        me = get_object_or_404(MonthEnd, pk=pk)
        if me.is_closed:
            messages.info(request, f"{me.period_label} zaten kapalı.")
        else:
            me.close(request.user)
            messages.success(request, f"{me.period_label} kapatıldı. Değerler dondurulmuştur.")
        return redirect("month_end:update", pk=me.pk)


class MonthReopenView(AdminRequiredMixin, View):
    """Kapalı ayı yeniden açar (yalnızca Admin). Değerler güncel satışlara göre yeniden hesaplanır."""
    http_method_names = ["post"]

    def post(self, request, pk):
        me = get_object_or_404(MonthEnd, pk=pk)
        if me.is_closed:
            me.reopen()
            messages.success(request, f"{me.period_label} yeniden açıldı; değerler güncel satışlara göre hesaplandı.")
        return redirect("month_end:update", pk=me.pk)
