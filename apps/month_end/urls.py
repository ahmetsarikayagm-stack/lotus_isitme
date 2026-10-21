from django.urls import path

from .report_views import MonthCloseView, MonthReopenView, MonthReportView, YearReportView
from .views import MonthEndCrud

app_name = "month_end"
urlpatterns = MonthEndCrud.urls() + [
    path("<int:pk>/rapor/pdf/", MonthReportView.as_view(fmt="pdf"), name="report_pdf"),
    path("<int:pk>/rapor/excel/", MonthReportView.as_view(fmt="xlsx"), name="report_xlsx"),
    path("<int:pk>/kapat/", MonthCloseView.as_view(), name="close"),
    path("<int:pk>/ac/", MonthReopenView.as_view(), name="reopen"),
    path("yillik/<int:year>/pdf/", YearReportView.as_view(fmt="pdf"), name="year_report_pdf"),
    path("yillik/<int:year>/excel/", YearReportView.as_view(fmt="xlsx"), name="year_report_xlsx"),
]
