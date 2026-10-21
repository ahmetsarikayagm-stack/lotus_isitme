from apps.core.crud import Card, Col, CrudConfig, Filter, choices_from
from apps.payments.models import PaymentMethod

from .forms import BankForm
from .models import Bank


class BankCrud(CrudConfig):
    model = Bank
    form_class = BankForm
    module_key = "banks"
    namespace = "banks"
    singular = "Banka"
    plural = "Bankalar"
    search_placeholder = "Banka ara..."
    search_fields = ("name", "payment_method__name")
    ordering = ("payment_method__name", "name")
    select_related = ("payment_method",)
    columns = (
        Col("Banka", "name", "name", link=True),
        Col("Ödeme yöntemi", "payment_method.name", "payment_method__name"),
        Col("Oluşturulma", "created_at", "created_at", kind="date"),
    )
    filters = (Filter("odeme", "Ödeme yöntemi", "payment_method_id", choices_from(PaymentMethod)),)
    cards = (Card("Banka Bilgileri", ("payment_method", "name")),)
