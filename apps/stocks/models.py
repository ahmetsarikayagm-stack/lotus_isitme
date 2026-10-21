from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import AuditModel, DeleteOldFilesMixin, SoftDeleteModel

LOW_STOCK_THRESHOLD = 2


class Stock(DeleteOldFilesMixin, SoftDeleteModel, AuditModel):
    category = models.ForeignKey("categories.Category", verbose_name="Kategori", on_delete=models.PROTECT, related_name="stocks")
    brand = models.ForeignKey("brands.Brand", verbose_name="Marka", on_delete=models.PROTECT, related_name="stocks")
    model = models.ForeignKey("models_app.DeviceModel", verbose_name="Model", on_delete=models.PROTECT, related_name="stocks")
    price = models.DecimalField("Fiyat (₺)", max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    quantity = models.PositiveIntegerField("Adet", default=1)
    image = models.ImageField("Ürün resmi", upload_to="stocks/%Y/%m/", blank=True, null=True)
    description = models.TextField("Açıklama", blank=True)

    file_fields = ("image",)

    class Meta:
        verbose_name = "Stok"
        verbose_name_plural = "Stoklar"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.brand} {self.model}"

    @property
    def is_low(self) -> bool:
        return self.quantity <= LOW_STOCK_THRESHOLD

    def clean(self):
        errors = {}
        if self.brand_id and self.category_id and self.brand.category_id != self.category_id:
            errors["brand"] = "Seçilen marka bu kategoriye ait değil."
        if self.model_id and self.brand_id and self.model.brand_id != self.brand_id:
            errors["model"] = "Seçilen model bu markaya ait değil."
        if errors:
            raise ValidationError(errors)
