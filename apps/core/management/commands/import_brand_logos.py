"""Bir klasördeki logo dosyalarını marka adına göre eşleyip markalara yükler."""
import re
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from PIL import Image, UnidentifiedImageError

from apps.brands.models import Brand

EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
_TR = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")


def normalize(text: str) -> str:
    """'Re Sound', 'resound', 'ReSound.png' -> 'resound' (Türkçe harf, boşluk ve noktalama duyarsız)."""
    return re.sub(r"[^a-z0-9]", "", text.translate(_TR).lower())


class Command(BaseCommand):
    help = (
        "Klasördeki logo dosyalarını (örn. phonak.png, resound.jpg) marka adına göre eşleyip yükler. "
        "Mevcut logoların (yer tutucular dahil) üzerine yazar."
    )

    def add_arguments(self, parser):
        parser.add_argument("klasor", help="Logo dosyalarının bulunduğu klasör")

    def handle(self, *args, **options):
        folder = Path(options["klasor"])
        if not folder.is_dir():
            raise CommandError(f"Klasör bulunamadı: {folder}")

        by_key = {}
        for brand in Brand.objects.all():
            by_key.setdefault(normalize(brand.name), []).append(brand)

        done, unmatched, invalid = [], [], []
        for file in sorted(folder.iterdir()):
            if file.suffix.lower() not in EXTENSIONS:
                continue
            brands = by_key.get(normalize(file.stem))
            if not brands:
                unmatched.append(file.name)
                continue
            try:
                Image.open(file).verify()
            except (UnidentifiedImageError, OSError):
                invalid.append(file.name)
                continue
            data = file.read_bytes()
            for brand in brands:
                brand.logo.save(f"{brand.pk}-{normalize(brand.name)}{file.suffix.lower()}", ContentFile(data), save=True)
            done.append(f"{file.name} → {', '.join(b.name for b in brands)}")

        for line in done:
            self.stdout.write(self.style.SUCCESS(f"  ✓ {line}"))
        self.stdout.write(self.style.SUCCESS(f"{len(done)} logo yüklendi."))
        if unmatched:
            self.stdout.write(self.style.WARNING("Eşleşen marka bulunamadı: " + ", ".join(unmatched)))
        if invalid:
            self.stdout.write(self.style.ERROR("Geçerli görsel değil: " + ", ".join(invalid)))
        missing = sorted(b.name for brands in by_key.values() for b in brands if not b.logo)
        if missing:
            self.stdout.write(self.style.WARNING("Logosu hâlâ olmayan markalar: " + ", ".join(missing)))
