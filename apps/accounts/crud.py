from django.contrib.auth.models import Group
from django.db.models import Count

from apps.core.crud import Card, Col, CrudConfig, CrudError, Filter

from .crud_forms import GroupForm, UserForm
from .models import Role, User


class UserCrud(CrudConfig):
    model = User
    form_class = UserForm
    module_key = "users"
    namespace = "users"
    singular = "Kullanıcı"
    plural = "Kullanıcılar"
    search_placeholder = "Kullanıcı adı, ad, e-posta veya telefon ara..."
    search_fields = ("username", "first_name", "last_name", "email", "phone")
    ordering = ("first_name", "username")
    columns = (
        Col("Kullanıcı Adı", "username", "username", link=True),
        Col("Ad Soyad", "display_name", "first_name"),
        Col("Rol", "get_role_display", "role", kind="badge"),
        Col("Telefon", "phone"),
        Col("Aktif", "is_active", "is_active", kind="bool"),
        Col("Son Giriş", "last_login", "last_login", kind="datetime"),
    )
    filters = (
        Filter("rol", "Rol", "role", lambda: list(Role.choices)),
        Filter("durum", "Durum", "is_active", lambda: [("true", "Aktif"), ("false", "Pasif")]),
    )
    cards = (
        Card("Hesap Bilgileri", ("username", "first_name", "last_name", "email", "phone")),
        Card("Yetki", ("role", "is_active", "groups"), "Rol, hangi sayfaları görebileceğini belirler."),
        Card("Şifre", ("password1", "password2")),
    )

    @classmethod
    def form_kwargs(cls, request):
        return {"request_user": request.user}

    @classmethod
    def delete_object(cls, request, obj):
        if obj.pk == request.user.pk:
            raise CrudError("Kendi hesabınızı silemezsiniz.")
        if obj.is_admin_role and not User.objects.filter(role=Role.ADMIN, is_active=True).exclude(pk=obj.pk).exists():
            raise CrudError("Sistemdeki son aktif yönetici silinemez.")
        obj.delete()


class GroupCrud(CrudConfig):
    model = Group
    form_class = GroupForm
    module_key = "groups"
    namespace = "groups"
    singular = "Grup"
    plural = "Gruplar"
    search_placeholder = "Grup ara..."
    search_fields = ("name",)
    ordering = ("name",)
    columns = (
        Col("Grup Adı", "name", "name", link=True),
        Col("Kullanıcı", "user_count", "user_count", kind="badge"),
        Col("İzin", "perm_count", "perm_count", kind="badge"),
    )
    cards = (
        Card("Grup Bilgileri", ("name",), columns=1),
        Card("İzinler", ("permissions",), columns=1),
    )

    @classmethod
    def get_queryset(cls, request):
        return Group.objects.annotate(user_count=Count("user", distinct=True), perm_count=Count("permissions", distinct=True))
