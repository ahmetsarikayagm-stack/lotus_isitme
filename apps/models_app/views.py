from apps.brands.models import Brand
from apps.categories.models import Category
from apps.core.crud import Card, Col, CrudConfig, Filter, choices_from

from .forms import DeviceModelForm
from .models import DeviceModel


class DeviceModelCrud(CrudConfig):
    model = DeviceModel
    form_class = DeviceModelForm
    module_key = "models"
    namespace = "models_app"
    singular = "Model"
    plural = "Modeller"
    search_placeholder = "Model, marka veya kategori ara..."
    search_fields = ("name", "brand__name", "brand__category__name")
    ordering = ("brand__category__name", "brand__name", "name")
    select_related = ("brand", "brand__category")
    columns = (
        Col("Model", "name", "name", link=True),
        Col("Marka", "brand.name", "brand__name"),
        Col("Kategori", "brand.category.name", "brand__category__name"),
        Col("Oluşturulma", "created_at", "created_at", kind="date"),
    )
    filters = (
        Filter("kategori", "Kategori", "brand__category_id", choices_from(Category)),
        Filter("marka", "Marka", "brand_id", choices_from(Brand, label=lambda b: f"{b.name} ({b.category.name})")),
    )
    cards = (Card("Model Bilgileri", ("brand", "name")),)
