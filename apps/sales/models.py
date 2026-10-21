from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.models import AuditModel, SoftDeleteModel

ZERO = Decimal("0")


class Sale(SoftDeleteModel, AuditModel):
    """Satış başlığı: bir hastanın tek alışverişi. Ürünler `items` (SaleItem) altında tutulur."""

    patient = models.ForeignKey("patients.Patient", verbose_name="Hasta", on_delete=models.PROTECT, related_name="sales")
    sale_date = models.DateField("Satış tarihi", default=timezone.localdate)

    payment_method = models.ForeignKey("payments.PaymentMethod", verbose_name="Ödeme yöntemi", on_delete=models.PROTECT, related_name="sales")
    bank = models.ForeignKey("banks.Bank", verbose_name="Banka", on_delete=models.PROTECT, null=True, blank=True, related_name="sales")

    discount = models.DecimalField("İndirim (₺)", max_digits=12, decimal_places=2, default=ZERO, validators=[MinValueValidator(ZERO)])
    deposit = models.DecimalField("Kapora (₺)", max_digits=12, decimal_places=2, default=ZERO, validators=[MinValueValidator(ZERO)])
    total = models.DecimalField("Toplam (₺)", max_digits=14, decimal_places=2, default=ZERO, editable=False,
                                help_text="Kalemlerin toplamı − indirim")
    remaining = models.DecimalField("Kalan (₺)", max_digits=14, decimal_places=2, default=ZERO, editable=False)

    audio_file = models.FileField(
        "Odyo dosyası", upload_to="sales/audio/%Y/%m/", blank=True, null=True,
        validators=[FileExtensionValidator(["pdf", "jpg", "jpeg", "png", "mp3", "wav", "m4a"])],
    )
    report_file = models.FileField(
        "Rapor dosyası", upload_to="sales/reports/%Y/%m/", blank=True, null=True,
        validators=[FileExtensionValidator(["pdf", "jpg", "jpeg", "png", "doc", "docx"])],
    )
    notes = models.TextField("Notlar", blank=True)

    class Meta:
        verbose_name = "Satış"
        verbose_name_plural = "Satışlar"
        ordering = ["-sale_date", "-pk"]
        indexes = [models.Index(fields=["sale_date"])]

    def __str__(self):
        return f"{self.patient} – {self.sale_date:%d.%m.%Y}"

    # --- hesaplar
    @property
    def subtotal(self) -> Decimal:
        """İndirim öncesi kalem toplamı."""
        return self.total + (self.discount or ZERO)

    def recalculate(self) -> None:
        """Kalemlerden toplam ve kalanı yeniden hesaplar (kalemler kaydedildikten sonra çağrılır)."""
        subtotal = sum((i.line_total for i in SaleItem.objects.filter(sale_id=self.pk)), ZERO)
        self.total = subtotal - (self.discount or ZERO)
        self.remaining = self.total - (self.deposit or ZERO)

    # --- liste gösterimi (items prefetch edilmişse ek sorgu atmaz)
    @property
    def items_summary(self) -> str:
        parts = [f"{i.product}" + (f" ×{i.quantity}" if i.quantity > 1 else "") for i in self.items.all()]
        text = " + ".join(parts)
        return text if len(text) <= 70 else text[:69] + "…"

    @property
    def has_institution(self) -> bool:
        return any(i.institution_right for i in self.items.all())

    def clean(self):
        if self.payment_method_id and self.bank_id and self.bank.payment_method_id != self.payment_method_id:
            raise ValidationError({"bank": "Seçilen banka bu ödeme yöntemine ait değil."})


class SaleItemQuerySet(models.QuerySet):
    def alive(self):
        """Silinmemiş satışlara ait kalemler."""
        return self.filter(sale__is_deleted=False)


class SaleItem(models.Model):
    """Satıştaki tek ürün kalemi."""

    sale = models.ForeignKey(Sale, verbose_name="Satış", on_delete=models.CASCADE, related_name="items")
    category = models.ForeignKey("categories.Category", verbose_name="Kategori", on_delete=models.PROTECT, related_name="sale_items")
    product = models.ForeignKey("stocks.Stock", verbose_name="Ürün", on_delete=models.PROTECT, related_name="sale_items")
    quantity = models.PositiveIntegerField("Adet", default=1, validators=[MinValueValidator(1)])
    unit_price = models.DecimalField("Birim fiyat (₺)", max_digits=12, decimal_places=2, validators=[MinValueValidator(ZERO)])
    unit_cost = models.DecimalField(
        "Birim maliyet (₺)", max_digits=12, decimal_places=2, default=ZERO, editable=False,
        help_text="Satış anındaki stok fiyatı; sonradan fiyat değişse de bu kayıt etkilenmez.",
    )
    institution_right = models.BooleanField("Kurum hakkı (SGK)", default=False)
    warranty_end = models.DateField("Garanti bitiş", null=True, blank=True)
    product_life = models.PositiveSmallIntegerField("Ürün ömrü (yıl)", null=True, blank=True)

    objects = SaleItemQuerySet.as_manager()

    class Meta:
        verbose_name = "Satış Kalemi"
        verbose_name_plural = "Satış Kalemleri"
        ordering = ["pk"]

    def __str__(self):
        return f"{self.product} ×{self.quantity}"

    @property
    def line_total(self) -> Decimal:
        return (self.unit_price or ZERO) * (self.quantity or 0)

    def clean(self):
        if self.product_id and self.category_id and self.product.category_id != self.category_id:
            raise ValidationError({"product": "Seçilen ürün bu kategoriye ait değil."})
