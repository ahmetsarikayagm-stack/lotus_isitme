from django.db.models import Count

from apps.core.crud import Card, Col, CrudConfig

from .forms import CategoryForm
from .models import Category


class CategoryCrud(CrudConfig):
    model = Category
    form_class = CategoryForm
    module_key = "categories"
    namespace = "categories"
    singular = "Kategori"
    plural = "Kategoriler"
    search_placeholder = "Kategori ara..."
    search_fields = ("name",)
    ordering = ("name",)
    columns = (
        Col("Ad", "name", "name", link=True),
        Col("Marka sayısı", "brand_count", "brand_count", kind="badge"),
        Col("Oluşturulma", "created_at", "created_at", kind="date"),
    )
    cards = (Card("Kategori", ("name",), columns=1),)

    @classmethod
    def get_queryset(cls, request):
        return Category.objects.annotate(brand_count=Count("brands"))
