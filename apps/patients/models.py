from django.db import models
from django.db.models import Q

from apps.core.models import AuditModel, SoftDeleteModel
from apps.core.validators import phone_validator, validate_tc_no


class Patient(SoftDeleteModel, AuditModel):
    full_name = models.CharField("Ad Soyad", max_length=150)
    tc_no = models.CharField("T.C. Kimlik No", max_length=11, validators=[validate_tc_no])
    phone = models.CharField("Telefon", max_length=20, validators=[phone_validator])
    phone2 = models.CharField("2. Telefon", max_length=20, blank=True, validators=[phone_validator])
    address = models.TextField("Adres", blank=True)
    notes = models.TextField("Notlar", blank=True)

    class Meta:
        verbose_name = "Hasta"
        verbose_name_plural = "Hastalar"
        ordering = ["full_name"]
        indexes = [models.Index(fields=["full_name"])]
        constraints = [
            # Soft delete edilmiş hastanın T.C.'si tekrar kullanılabilsin diye koşullu unique
            models.UniqueConstraint(
                fields=["tc_no"], condition=Q(is_deleted=False), name="uniq_patient_tc_alive",
                violation_error_message="Bu T.C. kimlik numarasıyla kayıtlı bir hasta zaten var.",
            ),
        ]

    def __str__(self):
        return self.full_name
