from django.contrib.auth import get_user_model
from django.db.models import Count, Q

from apps.core.crud import Card, Col, CrudConfig, Filter, choices_from

from .forms import PatientForm
from .models import Patient

User = get_user_model()


class PatientCrud(CrudConfig):
    model = Patient
    form_class = PatientForm
    module_key = "patients"
    namespace = "patients"
    singular = "Hasta"
    plural = "Hastalar"
    search_placeholder = "Ad soyad, T.C. veya telefon ara..."
    search_fields = ("full_name", "tc_no", "phone", "phone2")
    ordering = ("full_name",)
    columns = (
        Col("Ad Soyad", "full_name", "full_name", link=True),
        Col("T.C. No", "tc_no", "tc_no"),
        Col("Telefon", "phone", "phone"),
        Col("2. Telefon", "phone2"),
        Col("Satış", "sale_count", "sale_count", kind="badge"),
        Col("Kaydeden", "created_by.display_name", "created_by__first_name"),
        Col("Kayıt Tarihi", "created_at", "created_at", kind="date"),
    )
    filters = (Filter("kaydeden", "Kaydeden", "created_by_id", choices_from(User, label=lambda u: u.display_name)),)
    cards = (
        Card("Kişisel Bilgiler", ("full_name", "tc_no"), "Hastanın kimlik bilgileri."),
        Card("İletişim", ("phone", "phone2", "address"), "Telefon ve adres bilgileri."),
        Card("Notlar", ("notes",), columns=1),
    )

    @classmethod
    def get_queryset(cls, request):
        return Patient.objects.select_related("created_by").annotate(
            sale_count=Count("sales", filter=Q(sales__is_deleted=False))
        )
