from django.core.management.base import BaseCommand

from apps.banks.models import Bank
from apps.brands.models import Brand
from apps.categories.models import Category
from apps.payments.models import PaymentMethod

PAYMENTS = ["Nakit", "Kredi Kartı", "Havale / EFT", "Senet", "Kurum (SGK)"]
CATEGORIES = ["İşitme Cihazı", "Pil", "Kulak Kalıbı", "Aksesuar"]
BANKS = ["Ziraat Bankası", "İş Bankası", "Garanti BBVA", "Akbank", "Yapı Kredi", "Halkbank", "VakıfBank", "QNB", "DenizBank"]
BANK_PAYMENTS = ["Kredi Kartı", "Havale / EFT"]
BRANDS = {"İşitme Cihazı": ["Phonak", "Oticon", "Signia", "Widex", "ReSound", "Starkey"]}


class Command(BaseCommand):
    help = "Varsayılan ödeme yöntemi, banka, kategori ve marka kayıtlarını ekler (tekrar çalıştırılabilir)."

    def handle(self, *args, **options):
        pm = {n: PaymentMethod.objects.get_or_create(name=n)[0] for n in PAYMENTS}
        cats = {n: Category.objects.get_or_create(name=n)[0] for n in CATEGORIES}
        for method in BANK_PAYMENTS:
            for bank in BANKS:
                Bank.objects.get_or_create(name=bank, payment_method=pm[method])
        for cat, names in BRANDS.items():
            for name in names:
                Brand.objects.get_or_create(name=name, category=cats[cat])
        self.stdout.write(self.style.SUCCESS("Varsayılan veriler eklendi."))
