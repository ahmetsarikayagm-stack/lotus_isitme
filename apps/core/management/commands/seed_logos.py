"""Logosu olmayan markalara yer tutucu logo üretir (gerçek logoları ezmez)."""
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from apps.brands.models import Brand
from apps.core.placeholder_art import make_brand_logo


class Command(BaseCommand):
    help = "Logosu olmayan markalara örnek (yer tutucu) logo ekler. Yüklediğiniz logolara dokunmaz."

    def handle(self, *args, **options):
        count = 0
        for brand in Brand.objects.filter(logo=""):
            brand.logo.save(f"{brand.pk}-{brand.name.lower().replace(' ', '-')}.png", ContentFile(make_brand_logo(brand.name)), save=True)
            count += 1
        self.stdout.write(self.style.SUCCESS(f"{count} markaya örnek logo eklendi."))
