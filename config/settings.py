"""Lotus İşitme Ankara - İşitme Cihazı Stok & Hasta Yönetim Sistemi."""
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, True))
environ.Env.read_env(BASE_DIR / ".env")

# ------------------------------------------------------------------ Güvenlik
# Güvenlik ayarları şimdilik geliştirme modunda (production sertleştirmesi sonra yapılacak).
DEBUG = env("DEBUG")
SECRET_KEY = env("SECRET_KEY", default="dev-secret-key-degistir-sonra")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# ------------------------------------------------------------------ Uygulamalar
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.humanize",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "crispy_forms",
    "crispy_tailwind",
]

LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.payments",
    "apps.banks",
    "apps.categories",
    "apps.brands",
    "apps.models_app",
    "apps.patients",
    "apps.stocks",
    "apps.sales",
    "apps.month_end",
    "apps.dashboard",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.accounts.context_processors.sidebar_menu",
                "apps.core.context_processors.company",
            ],
        },
    },
]

# ------------------------------------------------------------------ Veritabanı
# DATABASE_URL boşsa SQLite; PostgreSQL için: postgres://user:pass@host:5432/db
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ------------------------------------------------------------------ Kimlik doğrulama
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard:index"
LOGOUT_REDIRECT_URL = "accounts:login"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

SESSION_COOKIE_AGE = 60 * 60 * 12  # 12 saat
SESSION_SAVE_EVERY_REQUEST = True

# ------------------------------------------------------------------ Yerelleştirme
LANGUAGE_CODE = "tr"
TIME_ZONE = "Europe/Istanbul"
USE_I18N = True
USE_TZ = True
USE_THOUSAND_SEPARATOR = True

# ------------------------------------------------------------------ Statik & Medya
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# Yükleme limitleri (odyo / rapor dosyaları için)
DATA_UPLOAD_MAX_MEMORY_SIZE = 25 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# ------------------------------------------------------------------ Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwind"
CRISPY_TEMPLATE_PACK = "tailwind"

# ------------------------------------------------------------------ Firma bilgileri
# Tüm sayfaların ve PDF / Excel raporlarının alt bilgisinde (footer) görünür.
COMPANY_NAME = "Lotus İşitme Cihazları"
COMPANY_ADDRESS = "Fidan Mahallesi, Mithatpaşa Cd. No:33 D:1, 06946 Çankaya/Ankara"
COMPANY_PHONE = "0553 111 11 06"
COMPANY_EMAIL = "info@lotusisitme.com"
