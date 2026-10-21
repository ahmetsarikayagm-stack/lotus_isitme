from django import forms
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.password_validation import validate_password

from apps.core.forms import TailwindFormMixin

from .models import Role, User

APP_LABELS = ["patients", "stocks", "sales", "month_end", "payments", "banks", "categories", "brands", "models_app"]
ACTIONS = {"add": "Ekle", "change": "Düzenle", "delete": "Sil", "view": "Görüntüle"}


class UserForm(TailwindFormMixin, forms.ModelForm):
    password1 = forms.CharField(label="Şifre", strip=False, required=False,
                                widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    password2 = forms.CharField(label="Şifre (tekrar)", strip=False, required=False,
                                widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "phone", "role", "is_active", "groups"]
        widgets = {"groups": forms.CheckboxSelectMultiple}
        labels = {"is_active": "Hesap aktif"}

    def __init__(self, *args, request_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request_user = request_user
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        self.fields["groups"].required = False
        self.fields["groups"].label = "Gruplar"
        self.fields["is_active"].help_text = "Pasif kullanıcılar sisteme giriş yapamaz."
        if self.instance.pk:
            self.fields["password1"].help_text = "Değiştirmek istemiyorsanız boş bırakın."
        else:
            self.fields["password1"].required = True
            self.fields["password2"].required = True

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 or p2:
            if p1 != p2:
                self.add_error("password2", "Şifreler eşleşmiyor.")
            elif p1:
                try:
                    validate_password(p1, self.instance)
                except forms.ValidationError as exc:
                    self.add_error("password1", exc)

        if self.instance.pk:
            role, active = cleaned.get("role"), cleaned.get("is_active")
            if self.request_user and self.instance.pk == self.request_user.pk:
                if role is not None and role != Role.ADMIN and self.instance.is_admin_role:
                    self.add_error("role", "Kendi yönetici rolünüzü değiştiremezsiniz.")
                if active is False:
                    self.add_error("is_active", "Kendi hesabınızı pasif yapamazsınız.")
            elif self.instance.is_admin_role and (role != Role.ADMIN or active is False):
                others = User.objects.filter(role=Role.ADMIN, is_active=True).exclude(pk=self.instance.pk)
                if not others.exists():
                    self.add_error(None, "Sistemde en az bir aktif yönetici kalmalıdır.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get("password1"):
            user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            self.save_m2m()
        return user


class GroupForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Group
        fields = ["name", "permissions"]
        widgets = {"permissions": forms.CheckboxSelectMultiple}
        labels = {"name": "Grup adı", "permissions": "İzinler"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        perms = (Permission.objects.filter(content_type__app_label__in=APP_LABELS)
                 .select_related("content_type").order_by("content_type__app_label", "codename"))
        self.fields["permissions"].queryset = perms
        self.fields["permissions"].required = False

        def label(p):
            model = p.content_type.model_class()
            name = model._meta.verbose_name_plural if model else p.content_type.model
            return f"{name}: {ACTIONS.get(p.codename.split('_')[0], p.codename)}"

        self.fields["permissions"].label_from_instance = label
