"""Örnek veri: hasta, stok, satış ve ay sonu kayıtları (demo / deneme amaçlı)."""
import random
from datetime import date
from decimal import Decimal as D

from django.core.management import call_command
from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.banks.models import Bank
from apps.brands.models import Brand
from apps.categories.models import Category
from apps.models_app.models import DeviceModel
from apps.month_end.models import MonthEnd
from apps.patients.models import Patient
from apps.payments.models import PaymentMethod
from apps.sales import services
from apps.sales.models import Sale
from apps.stocks.models import Stock

PATIENTS = [
    ("Ahmet Yılmaz", "0532 111 22 01"), ("Fatma Demir", "0533 222 33 02"), ("Mehmet Kaya", "0535 333 44 03"),
    ("Ayşe Çelik", "0536 444 55 04"), ("Mustafa Şahin", "0537 555 66 05"), ("Emine Yıldız", "0538 666 77 06"),
    ("Hüseyin Aydın", "0539 777 88 07"), ("Zeynep Özdemir", "0541 888 99 08"), ("İbrahim Arslan", "0542 999 00 09"),
    ("Hatice Doğan", "0543 123 45 10"), ("Ali Koç", "0544 234 56 11"), ("Sevgi Kurt", "0545 345 67 12"),
]

# (marka, kategori, model, maliyet, satış fiyatı)
DEVICES = [
    ("Phonak", "İşitme Cihazı", "Audéo Lumity L90", 38000, 62000),
    ("Phonak", "İşitme Cihazı", "Audéo Lumity L70", 30000, 51000),
    ("Oticon", "İşitme Cihazı", "More 1", 36000, 59000),
    ("Oticon", "İşitme Cihazı", "Real 2", 27000, 45000),
    ("Signia", "İşitme Cihazı", "Pure Charge&Go 7X", 29000, 48000),
    ("Signia", "İşitme Cihazı", "Styletto X", 33000, 54000),
    ("Widex", "İşitme Cihazı", "Moment 440", 31000, 52000),
    ("ReSound", "İşitme Cihazı", "Omnia 9", 34000, 56000),
    ("Rayovac", "Pil", "Pil No:312 (6'lı paket)", 90, 180),
]


def make_tc(base9: int) -> str:
    """Geçerli (sağlama hanesi doğru) T.C. kimlik no üretir."""
    d = [int(c) for c in str(base9)]
    d.append((sum(d[0:9:2]) * 7 - sum(d[1:8:2])) % 10)
    d.append(sum(d) % 10)
    return "".join(map(str, d))


def sale_date(rng, today, months_ago):
    y, m = today.year, today.month - months_ago
    while m <= 0:
        y, m = y - 1, m + 12
    day = rng.randint(1, 28)
    if (y, m) == (today.year, today.month):
        day = min(day, today.day)
    return date(y, m, day)


class Command(BaseCommand):
    help = "Deneme için örnek hasta, stok, satış ve ay sonu kayıtları ekler."

    def handle(self, *args, **options):
        if Patient.objects.exists() or Sale.objects.exists():
            self.stdout.write(self.style.WARNING(
                "Veritabanında zaten hasta/satış kaydı var; örnek veri eklenmedi.\n"
                "Temiz başlamak için db.sqlite3 dosyasını silip 'python manage.py migrate' çalıştırın."))
            return

        rng = random.Random(42)
        today = date.today()
        call_command("seed_defaults", verbosity=0)
        user = User.objects.filter(is_superuser=True).first() or User.objects.first()

        # --- Hastalar
        patients = [
            Patient.objects.create(full_name=name, tc_no=make_tc(100000001 + i * 7919), phone=phone, created_by=user,
                                   address="Çankaya / Ankara" if i % 2 == 0 else "Keçiören / Ankara")
            for i, (name, phone) in enumerate(PATIENTS)
        ]

        # --- Marka / model / stok
        stocks = []
        for brand_name, cat_name, model_name, cost, price in DEVICES:
            cat = Category.objects.get(name=cat_name)
            brand, _ = Brand.objects.get_or_create(name=brand_name, category=cat)
            model, _ = DeviceModel.objects.get_or_create(name=model_name, brand=brand)
            stock = Stock.objects.create(category=cat, brand=brand, model=model, price=D(cost), quantity=60,
                                         description="Örnek stok kaydı", created_by=user)
            stocks.append((stock, price))

        # --- Satışlar (son 4 ay; her satış birden fazla ürün içerebilir)
        methods = {m.name: m for m in PaymentMethod.objects.all()}
        devices, battery = stocks[:-1], stocks[-1]
        for i in range(20):
            method = methods[rng.choice(["Nakit", "Kredi Kartı", "Kredi Kartı", "Havale / EFT", "Kurum (SGK)"])]
            bank = None
            if method.name in ("Kredi Kartı", "Havale / EFT"):
                bank = rng.choice(list(Bank.objects.filter(payment_method=method)))
            d = sale_date(rng, today, rng.choice([0, 0, 1, 1, 2, 3]))
            sgk = method.name == "Kurum (SGK)" or rng.random() < 0.15

            stock, price = rng.choice(devices)                       # ana cihaz (1-2 adet)
            lines = [(stock, price, rng.choice([1, 2, 2]))]
            if rng.random() < 0.25:                                  # bazen farklı modelde ikinci cihaz
                s2, p2 = rng.choice(devices)
                lines.append((s2, p2, 1))
            if rng.random() < 0.45:                                  # sıklıkla pil paketi
                lines.append((battery[0], battery[1], rng.randint(2, 4)))

            items, subtotal = [], D(0)
            for st, pr, qty in lines:
                is_battery = st.category.name == "Pil"
                subtotal += D(pr) * qty
                items.append({
                    "id": None, "category": st.category, "product": st, "quantity": qty, "unit_price": D(pr),
                    "institution_right": sgk and not is_battery,
                    "warranty_end": None if is_battery else date(d.year + 2, d.month, d.day),
                    "product_life": None if is_battery else 5,
                })
            discount = D(rng.choice([0, 0, 0, 1000, 2500]))
            total = subtotal - discount
            deposit = min((total * D(str(rng.choice([0, 0.2, 0.5, 1]))) / 100).quantize(D("1")) * 100, total)
            sale = Sale(patient=patients[i % len(patients)], payment_method=method, bank=bank, sale_date=d,
                        discount=discount, deposit=deposit, notes="Örnek satış kaydı", created_by=user)
            services.save_sale(sale, items)

        call_command("seed_logos", verbosity=0)  # örnek marka logoları

        # Stok ekranında "az kalan / tükendi" görünsün
        Stock.objects.filter(model__name="Styletto X").update(quantity=1)
        Stock.objects.filter(model__name="Real 2").update(quantity=0)

        # --- Ay sonu (satış olan her ay için)
        months = sorted({(s.sale_date.year, s.sale_date.month) for s in Sale.objects.all()})
        for y, m in months:
            MonthEnd.objects.update_or_create(year=y, month=m, defaults=dict(
                rent=D(25000), electricity=D(rng.randint(2800, 4200)), water=D(rng.randint(400, 800)),
                internet=D(900), salary=D(45000), accounting=D(4000), general_expenses=D(rng.randint(1500, 3500)),
                created_by=user))

        self.stdout.write(self.style.SUCCESS(
            f"Örnek veri eklendi: {Patient.objects.count()} hasta, {Stock.objects.count()} stok, "
            f"{Sale.objects.count()} satış, {MonthEnd.objects.count()} ay sonu kaydı."))
