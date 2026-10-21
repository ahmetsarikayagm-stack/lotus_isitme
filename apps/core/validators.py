from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

phone_validator = RegexValidator(r"^[0-9+()\-\s]{7,20}$", "Geçerli bir telefon numarası girin.")


def validate_tc_no(value: str) -> None:
    """T.C. kimlik numarası: 11 hane, ilk hane 0 değil, resmi sağlama algoritması."""
    v = str(value)
    if not (v.isdigit() and len(v) == 11 and v[0] != "0"):
        raise ValidationError("T.C. kimlik numarası 11 haneli olmalı ve 0 ile başlamamalıdır.")
    d = [int(c) for c in v]
    if (sum(d[0:9:2]) * 7 - sum(d[1:8:2])) % 10 != d[9] or sum(d[:10]) % 10 != d[10]:
        raise ValidationError("Geçersiz T.C. kimlik numarası.")
