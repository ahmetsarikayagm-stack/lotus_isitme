from django.contrib.auth.views import LoginView, LogoutView

from .forms import LoginForm


class LotusLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class LotusLogoutView(LogoutView):
    """Django 5: yalnızca POST kabul eder (CSRF korumalı form ile çağrılmalı)."""
