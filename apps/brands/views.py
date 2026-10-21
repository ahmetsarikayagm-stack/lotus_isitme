from django.db.models import Count

from apps.categories.models import Category
from apps.core.crud import Card, Col, CrudConfig, Filter, choices_from

from .forms import BrandForm
from .models import Brand


class BrandCrud(CrudConfig):
    model = Brand
    form_class = BrandForm
    module_key = "brands"
    namespace = "brands"
    singular = "Marka"
    plural = "Markalar"
    search_placeholder = "Marka ara..."
    search_fields = ("name", "category__name")
    ordering = ("category__name", "name")
    select_related = ("category",)
    columns = (
        Col("Logo", "logo", kind="logo"),
        Col("Marka", "name", "name", link=True),
        Col("Kategori", "category.name", "category__name"),
        Col("Model sayısı", "model_count", "model_count", kind="badge"),
        Col("Oluşturulma", "created_at", "created_at", kind="date"),
    )
    filters = (Filter("kategori", "Kategori", "category_id", choices_from(Category)),)
    cards = (
        Card("Marka Bilgileri", ("category", "name")),
        Card("Logo", ("logo",), "Stok listesinde ve ürün sayfasında marka adının yanında görünür.", columns=1),
    )

    @classmethod
    def get_queryset(cls, request):
        return Brand.objects.select_related("category").annotate(model_count=Count("models"))
