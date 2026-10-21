from django import forms
from django.contrib.auth.forms import AuthenticationForm

INPUT_CLASSES = (
    "block w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 text-sm "
    "text-slate-900 placeholder-slate-400 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/25 "
    "focus:outline-none"
)


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Kullanıcı adı",
        widget=forms.TextInput(
            attrs={"class": INPUT_CLASSES, "placeholder": "Kullanıcı adınız", "autofocus": True, "autocomplete": "username"}
        ),
    )
    password = forms.CharField(
        label="Şifre",
        strip=False,
        widget=forms.PasswordInput(
            attrs={"class": INPUT_CLASSES, "placeholder": "••••••••", "autocomplete": "current-password"}
        ),
    )

    error_messages = {
        "invalid_login": "Kullanıcı adı veya şifre hatalı.",
        "inactive": "Bu hesap pasif durumda. Lütfen yöneticiyle iletişime geçin.",
    }
