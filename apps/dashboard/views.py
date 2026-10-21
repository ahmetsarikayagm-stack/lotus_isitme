from django.views.generic import TemplateView

from apps.accounts.mixins import ModuleAccessMixin

from .services import get_dashboard_data


class DashboardView(ModuleAccessMixin, TemplateView):
    module_key = "dashboard"
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(get_dashboard_data())
        return ctx
