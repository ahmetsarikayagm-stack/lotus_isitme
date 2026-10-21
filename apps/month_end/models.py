from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.core.validators import MaxValueValidator, MinValueValidator

from apps.core.models import AuditModel

ZERO = Decimal("0")

MONTHS = [
    (1, "Ocak"), (2, "Şubat"), (3, "Mart"), (4, "Nisan"), (5, "Mayıs"), (6, "Haziran"),
    (7, "Temmuz"), (8, "Ağustos"), (9, "Eylül"), (10, "Ekim"), (11, "Kasım"), (12, "Aralık"),
]


def _money(label, **kw):
    return models.DecimalField(label, max_digits=14, decimal_places=2, default=ZERO, **kw)


class MonthEnd(AuditModel):
    year = models.PositiveSmallIntegerField("Yıl", validators=[MinValueValidator(2000), MaxValueValidator(2100)])
    month = models.PositiveSmallIntegerField("Ay", choices=MONTHS)

    rent = _money("Kira (₺)", validators=[MinValueValidator(ZERO)])
    electricity = _money("Elektrik (₺)", validators=[MinValueValidator(ZERO)])
    water = _money("Su (₺)", validators=[MinValueValidator(ZERO)])
    internet = _money("İnternet (₺)", validators=[MinValueValidator(ZERO)])
    salary = _money("Maaş (₺)", validators=[MinValueValidator(ZERO)])
    accounting = _money("Muhasebe (₺)", validators=[MinValueValidator(ZERO)])
    general_expenses = _money("Genel giderler (₺)", validators=[MinValueValidator(ZERO)])

    # Otomatik hesaplanan alanlar
    device_cost = _money("Cihaz maliyeti (₺)", editable=False)
    total_income = _money("Toplam gelir (₺)", editable=False)
    total_expense = _money("Toplam gider (₺)", editable=False)
    profit = _money("Kâr / Zarar (₺)", editable=False)

    # Dönem kapatma: kapalı ayın değerleri dondurulur, o aya ait satışlar değiştirilemez
    is_closed = models.BooleanField("Kapatıldı", default=False, db_index=True)
    closed_at = models.DateTimeField("Kapatılma zamanı", null=True, blank=True, editable=False)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Kapatan", on_delete=models.SET_NULL,
        null=True, blank=True, editable=False, related_name="closed_month_ends",
    )

    FIXED_EXPENSE_FIELDS = ("rent", "electricity", "water", "internet", "salary", "accounting", "general_expenses")

    class Meta:
        verbose_name = "Ay Sonu"
        verbose_name_plural = "Ay Sonu"
        ordering = ["-year", "-month"]
        constraints = [
            models.UniqueConstraint(fields=["year", "month"], name="uniq_month_end_period",
                                    violation_error_message="Bu dönem için ay sonu kaydı zaten var."),
        ]

    def __str__(self):
        return self.period_label

    @property
    def period_label(self) -> str:
        return f"{self.get_month_display()} {self.year}"

    @property
    def fixed_expenses(self) -> Decimal:
        return sum((getattr(self, f) or ZERO for f in self.FIXED_EXPENSE_FIELDS), ZERO)

    def calculate(self):
        """
        Gelir      = dönemdeki satışların net toplamı (kalemler − indirim)
        Cihaz maliyeti = satılan ürünlerin SATIŞ ANINDAKİ maliyeti (unit_cost) × adet
        Gider      = sabit giderler + cihaz maliyeti
        """
        from apps.sales.models import Sale, SaleItem

        money = DecimalField(max_digits=16, decimal_places=2)
        income = Sale.objects.filter(sale_date__year=self.year, sale_date__month=self.month).aggregate(t=Sum("total"))["t"]
        cost = SaleItem.objects.alive().filter(
            sale__sale_date__year=self.year, sale__sale_date__month=self.month
        ).aggregate(c=Sum(ExpressionWrapper(F("unit_cost") * F("quantity"), output_field=money)))["c"]
        self.total_income = income or ZERO
        self.device_cost = cost or ZERO
        self.total_expense = self.fixed_expenses + self.device_cost
        self.profit = self.total_income - self.total_expense

    def save(self, *args, **kwargs):
        if not self.is_closed:      # kapalı ay dondurulmuştur: değerler yeniden hesaplanmaz
            self.calculate()
        super().save(*args, **kwargs)

    def close(self, user=None):
        """Son kez hesaplar ve ayı dondurur."""
        self.calculate()
        self.is_closed = True
        self.closed_at = timezone.now()
        self.closed_by = user
        self.save()

    def reopen(self):
        """Ayı yeniden açar; değerler güncel satışlara göre tekrar hesaplanır."""
        self.is_closed = False
        self.closed_at = None
        self.closed_by = None
        self.save()

    @classmethod
    def is_period_closed(cls, year, month) -> bool:
        return cls.objects.filter(year=year, month=month, is_closed=True).exists()

    @classmethod
    def refresh(cls, year, month):
        """Satışlar değiştiğinde ilgili dönemin AÇIK ay sonu kaydını yeniden hesaplar."""
        for obj in cls.objects.filter(year=year, month=month, is_closed=False):
            obj.save()
