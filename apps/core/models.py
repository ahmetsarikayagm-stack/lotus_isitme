"""Tüm uygulamaların kullandığı ortak abstract modeller."""
from django.conf import settings
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField("Oluşturulma", auto_now_add=True)
    updated_at = models.DateTimeField("Güncellenme", auto_now=True)

    class Meta:
        abstract = True


class AuditModel(TimeStampedModel):
    """Kaydı oluşturan kullanıcıyı da tutar."""

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Oluşturan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
        related_name="%(app_label)s_%(class)s_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Son işlem yapan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
        related_name="%(app_label)s_%(class)s_updated",
    )

    class Meta:
        abstract = True

    @property
    def last_actor(self):
        """Son işlemi yapan kullanıcı (eski kayıtlarda henüz yoksa oluşturan)."""
        return self.updated_by or self.created_by

    @property
    def last_action_text(self):
        who = self.last_actor
        if who is None:
            return None
        return f"{who.display_name} · {timezone.localtime(self.updated_at):%d.%m.%Y %H:%M}"


class DeleteOldFilesMixin(models.Model):
    """Dosya/resim alanı değiştirildiğinde eski dosyayı diskten siler (Django bunu kendiliğinden yapmaz)."""

    file_fields: tuple = ()   # örn. ("logo",)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        old = {}
        if self.pk and self.file_fields:
            row = type(self)._base_manager.filter(pk=self.pk).values(*self.file_fields).first() or {}
            old = {name: row.get(name) for name in self.file_fields}
        super().save(*args, **kwargs)
        for name, old_name in old.items():
            current = getattr(self, name)
            if old_name and old_name != (current.name if current else ""):
                current.storage.delete(old_name)


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        return self.update(is_deleted=True, deleted_at=timezone.now())

    def hard_delete(self):
        return super().delete()

    def alive(self):
        return self.filter(is_deleted=False)

    def dead(self):
        return self.filter(is_deleted=True)

    def restore(self):
        return self.update(is_deleted=False, deleted_at=None)


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    """Varsayılan olarak silinmemiş kayıtları döndürür."""

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class AllObjectsManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    """Silinmiş kayıtlar dahil tüm kayıtlar."""


class SoftDeleteModel(models.Model):
    """Soft delete: `obj.delete()` kaydı silmez, is_deleted=True yapar."""

    is_deleted = models.BooleanField("Silindi", default=False, db_index=True)
    deleted_at = models.DateTimeField("Silinme zamanı", null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at"])
