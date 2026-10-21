from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.db import models


class Role(models.TextChoices):
    ADMIN = "admin", "Admin"
    SALES = "sales", "Satış Temsilcisi"


class UserManager(DjangoUserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", Role.ADMIN)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    Role = Role

    role = models.CharField("Rol", max_length=20, choices=Role.choices, default=Role.SALES)
    phone = models.CharField("Telefon", max_length=20, blank=True)

    objects = UserManager()

    class Meta:
        verbose_name = "Kullanıcı"
        verbose_name_plural = "Kullanıcılar"
        ordering = ["first_name", "last_name", "username"]

    def __str__(self):
        return self.display_name

    def save(self, *args, **kwargs):
        # Superuser her zaman Admin; Admin rolü Django admin'e girebilsin (is_staff).
        if self.is_superuser:
            self.role = Role.ADMIN
        self.is_staff = self.is_superuser or self.role == Role.ADMIN
        super().save(*args, **kwargs)

    @property
    def display_name(self) -> str:
        return self.get_full_name().strip() or self.username

    @property
    def is_admin_role(self) -> bool:
        return self.role == Role.ADMIN

    @property
    def is_sales_role(self) -> bool:
        return self.role == Role.SALES
