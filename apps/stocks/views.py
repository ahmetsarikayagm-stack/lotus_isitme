from apps.brands.models import Brand
from apps.categories.models import Category
from apps.core.crud import Card, Col, CrudConfig, Filter, choices_from

from .forms import StockForm
from .models import Stock


class StockCrud(CrudConfig):
    model = Stock
    form_class = StockForm
    module_key = "stocks"
    namespace = "stocks"
    singular = "Stok"
    plural = "Stoklar"
    form_template = "stocks/form.html"
    search_placeholder = "Model, marka, kategori veya açıklama ara..."
    search_fields = ("model__name", "brand__name", "category__name", "description")
    ordering = ("-created_at",)
    select_related = ("category", "brand", "model", "created_by", "updated_by")
    columns = (
        Col("Görsel", "image", kind="image"),
        Col("Model", "model.name", "model__name", link=True),
        Col("Marka", "brand", "brand__name", kind="brand"),
        Col("Kategori", "category.name", "category__name"),
        Col("Fiyat", "price", "price", kind="money"),
        Col("Adet", "quantity", "quantity", kind="qty"),
        Col("Eklenme", "created_at", "created_at", kind="date"),
        Col("Kaydeden", "created_by.display_name", "created_by__first_name"),
        Col("Son İşlem", "last_action_text", "updated_at"),
    )
    filters = (
        Filter("kategori", "Kategori", "category_id", choices_from(Category)),
        Filter("marka", "Marka", "brand_id", choices_from(Brand, label=lambda b: f"{b.name} ({b.category.name})")),
        Filter("stok", "Stok durumu", "quantity__lte", lambda: [("0", "Tükendi"), ("2", "Az kalan (≤2)")]),
    )
    cards = (
        Card("Ürün Bilgileri", ("category", "brand", "model"), "Önce kategori, sonra marka ve model seçin."),
        Card("Fiyat & Adet", ("price", "quantity")),
        Card("Görsel & Açıklama", ("image", "description"), columns=1),
    )
