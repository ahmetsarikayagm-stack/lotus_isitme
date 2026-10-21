from django.db import models

from apps.core.models import TimeStampedModel


class PaymentMethod(TimeStampedModel):
    name = models.CharField("Ad", max_length=100, unique=True)

    class Meta:
        verbose_name = "Ödeme Yöntemi"
        verbose_name_plural = "Ödemeler"
        ordering = ["name"]

    def __str__(self):
        return self.name
