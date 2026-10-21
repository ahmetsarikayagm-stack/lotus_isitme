from django.db.models import Count

from apps.core.crud import Card, Col, CrudConfig

from .forms import PaymentMethodForm
from .models import PaymentMethod


class PaymentCrud(CrudConfig):
    model = PaymentMethod
    form_class = PaymentMethodForm
    module_key = "payments"
    namespace = "payments"
    singular = "Ödeme Yöntemi"
    plural = "Ödemeler"
    search_placeholder = "Ödeme yöntemi ara..."
    search_fields = ("name",)
    ordering = ("name",)
    columns = (
        Col("Ad", "name", "name", link=True),
        Col("Banka sayısı", "bank_count", "bank_count", kind="badge"),
        Col("Oluşturulma", "created_at", "created_at", kind="date"),
    )
    cards = (Card("Ödeme Yöntemi", ("name",), columns=1),)

    @classmethod
    def get_queryset(cls, request):
        return PaymentMethod.objects.annotate(bank_count=Count("banks"))
