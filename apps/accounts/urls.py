from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("giris/", views.LotusLoginView.as_view(), name="login"),
    path("cikis/", views.LotusLogoutView.as_view(), name="logout"),
]
