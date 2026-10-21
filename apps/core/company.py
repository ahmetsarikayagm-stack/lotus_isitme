"""Firma bilgileri (alt bilgi / antet). Değerler config/settings.py içindeki COMPANY_* ayarlarından gelir."""
from django.conf import settings


def company_info() -> dict:
    return {
        "name": getattr(settings, "COMPANY_NAME", "Lotus İşitme Cihazları"),
        "address": getattr(settings, "COMPANY_ADDRESS", "Fidan Mahallesi, Mithatpaşa Cd. No:33 D:1, 06946 Çankaya/Ankara"),
        "phone": getattr(settings, "COMPANY_PHONE", "0553 111 11 06"),
        "email": getattr(settings, "COMPANY_EMAIL", "info@lotusisitme.com"),
    }
