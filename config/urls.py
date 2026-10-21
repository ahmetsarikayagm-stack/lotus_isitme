from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Lotus İşitme - Teknik Panel"
admin.site.site_title = "Lotus İşitme"
admin.site.index_title = "Teknik Yönetim"

urlpatterns = [
    path("django-admin/", admin.site.urls),  # minimal; asıl panel kendi frontend'imiz
    path("hesap/", include("apps.accounts.urls")),
    path("", include("apps.dashboard.urls")),
    path("hastalar/", include("apps.patients.urls")),
    path("odemeler/", include("apps.payments.urls")),
    path("bankalar/", include("apps.banks.urls")),
    path("kategoriler/", include("apps.categories.urls")),
    path("markalar/", include("apps.brands.urls")),
    path("modeller/", include("apps.models_app.urls")),
    path("stoklar/", include("apps.stocks.urls")),
    path("satislar/", include("apps.sales.urls")),
    path("ay-sonu/", include("apps.month_end.urls")),
    path("kullanicilar/", include("apps.accounts.user_urls")),
    path("gruplar/", include("apps.accounts.group_urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
