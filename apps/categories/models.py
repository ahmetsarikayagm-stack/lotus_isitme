from django.db import models

from apps.core.models import TimeStampedModel


class Category(TimeStampedModel):
    name = models.CharField("Ad", max_length=100, unique=True)

    class Meta:
        verbose_name = "Kategori"
        verbose_name_plural = "Kategoriler"
        ordering = ["name"]

    def __str__(self):
        return self.name
