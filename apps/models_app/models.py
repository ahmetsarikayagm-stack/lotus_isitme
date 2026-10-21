from django.db import models

from apps.core.models import TimeStampedModel


class DeviceModel(TimeStampedModel):
    """Marka altındaki cihaz modeli (Django 'Model' ile karışmasın diye DeviceModel)."""

    name = models.CharField("Ad", max_length=100)
    brand = models.ForeignKey(
        "brands.Brand", verbose_name="Marka",
        on_delete=models.PROTECT, related_name="models",
    )

    class Meta:
        verbose_name = "Model"
        verbose_name_plural = "Modeller"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["brand", "name"], name="uniq_model_per_brand",
                                    violation_error_message="Bu markada aynı isimde model zaten var."),
        ]

    def __str__(self):
        return self.name

    @property
    def category(self):
        return self.brand.category
