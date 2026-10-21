from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from .permissions import can_access


class ModuleAccessMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Modül bazlı erişim kontrolü. Kullanım:

        class PatientListView(ModuleAccessMixin, ListView):
            module_key = "patients"

    Anonim kullanıcı -> login'e yönlendirir, yetkisiz kullanıcı -> 403.
    """

    module_key: str | None = None

    def test_func(self):
        if self.module_key is None:
            raise NotImplementedError(f"{self.__class__.__name__}.module_key tanımlanmalı.")
        return can_access(self.request.user, self.module_key)


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Doğrudan role göre kontrol: allowed_roles = (Role.ADMIN,)"""

    allowed_roles: tuple = ()

    def test_func(self):
        user = self.request.user
        return user.is_superuser or user.role in self.allowed_roles


class AdminRequiredMixin(RoleRequiredMixin):
    from .models import Role as _Role

    allowed_roles = (_Role.ADMIN,)
