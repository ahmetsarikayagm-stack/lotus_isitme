from django.db import models

from apps.core.models import DeleteOldFilesMixin, TimeStampedModel


class Brand(DeleteOldFilesMixin, TimeStampedModel):
    name = models.CharField("Ad", max_length=100)
    category = models.ForeignKey(
        "categories.Category", verbose_name="Kategori",
        on_delete=models.PROTECT, related_name="brands",
    )
    logo = models.ImageField("Logo", upload_to="brands/", blank=True, null=True)

    file_fields = ("logo",)

    class Meta:
        verbose_name = "Marka"
        verbose_name_plural = "Markalar"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["category", "name"], name="uniq_brand_per_category",
                                    violation_error_message="Bu kategoride aynı isimde marka zaten var."),
        ]

    def __str__(self):
        return self.name
