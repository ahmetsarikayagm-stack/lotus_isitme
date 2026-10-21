from django.db import models

from apps.core.models import TimeStampedModel


class Bank(TimeStampedModel):
    name = models.CharField("Ad", max_length=100)
    payment_method = models.ForeignKey(
        "payments.PaymentMethod", verbose_name="Ödeme yöntemi",
        on_delete=models.PROTECT, related_name="banks",
    )

    class Meta:
        verbose_name = "Banka"
        verbose_name_plural = "Bankalar"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["payment_method", "name"], name="uniq_bank_per_payment_method",
                                    violation_error_message="Bu ödeme yönteminde aynı isimde banka zaten var."),
        ]

    def __str__(self):
        return self.name
