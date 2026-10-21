from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "first_name", "last_name", "role", "is_active")
    list_filter = ("role", "is_active", "groups")
    fieldsets = DjangoUserAdmin.fieldsets + (("Lotus", {"fields": ("role", "phone")}),)
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("Lotus", {"fields": ("first_name", "last_name", "role", "phone")}),
    )
