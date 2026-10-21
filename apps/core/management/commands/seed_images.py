"""Resmi olmayan stok kayıtlarına örnek (yer tutucu) ürün görseli üretir; marka logosu varsa görsele eklenir."""
import io
import re
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw, ImageFont

from apps.core.placeholder_art import colors_for
from apps.stocks.models import Stock

SIZE = 800
TR = str.maketrans("çğıöşüÇĞİÖŞÜéÉ", "cgiosuCGIOSUeE")  # yerleşik yazı tipi Türkçe karakter çizemeyebilir
GENERATED = re.compile(r"^stock-\d+(_\w+)?\.jpg$")      # bu komutun ürettiği dosya adları


def font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # eski Pillow
        return ImageFont.load_default()


def centered(draw, y, text, fnt, fill):
    w = draw.textlength(text, font=fnt)
    draw.text(((SIZE - w) / 2, y), text, font=fnt, fill=fill)


def draw_hearing_aid(d, accent):
    d.arc((190, 120, 530, 460), 180, 360, fill=accent, width=40)                 # kulak arkası kanca
    d.rounded_rectangle((190, 280, 230, 400), radius=20, fill=accent)             # ince tüp
    d.ellipse((165, 390, 255, 480), fill=accent)                                  # kulak kalıbı ucu
    d.ellipse((440, 260, 620, 560), fill=accent)                                  # gövde
    d.ellipse((490, 320, 570, 400), fill="white")                                 # mikrofon girişi
    d.ellipse((515, 345, 545, 375), fill=accent)


def draw_battery(d, accent):
    d.ellipse((250, 130, 550, 430), fill=accent)
    d.ellipse((300, 180, 500, 380), outline="white", width=10)
    d.rounded_rectangle((385, 215, 415, 345), radius=8, fill="white")
    d.rounded_rectangle((345, 265, 455, 295), radius=8, fill="white")


def _brand_logo(stock):
    try:
        if stock.brand.logo:
            return Image.open(stock.brand.logo.path).convert("RGBA")
    except (OSError, ValueError):
        pass
    return None


def make_image(stock) -> bytes:
    bg, accent = colors_for(stock.brand.name)
    img = Image.new("RGB", (SIZE, SIZE), bg)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((40, 40, SIZE - 40, SIZE - 40), radius=48, outline=accent, width=4)
    (draw_battery if stock.category.name == "Pil" else draw_hearing_aid)(d, accent)
    logo = _brand_logo(stock)
    if logo is not None:                                  # marka logosu varsa yazı yerine logoyu kullan
        logo.thumbnail((260, 82))
        img.paste(logo, ((SIZE - logo.width) // 2, 584), logo)
    else:
        centered(d, 560, stock.brand.name.translate(TR).upper(), font(64), "#0F172A")
    model = stock.model.name.translate(TR)
    centered(d, 684 if logo is not None else 650, model if len(model) <= 26 else model[:25] + "…", font(36), "#475569")
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=88)
    return buf.getvalue()


class Command(BaseCommand):
    help = "Görseli olmayan stok kayıtlarına örnek ürün resmi ekler."

    def add_arguments(self, parser):
        parser.add_argument("--yenile", action="store_true",
                            help="Daha önce bu komutla üretilmiş görselleri yeniler (örn. marka logosu eklendikten sonra); kendi fotoğraflarınıza dokunmaz")
        parser.add_argument("--force", action="store_true", help="Kendi yüklediğiniz fotoğraflar dahil TÜM görselleri yeniler")

    def handle(self, *args, **options):
        qs = Stock.objects.select_related("brand", "model", "category")
        if not options["force"] and not options["yenile"]:
            qs = qs.filter(image="") | qs.filter(image__isnull=True)
        count = 0
        for stock in qs:
            if options["yenile"] and not options["force"] and stock.image and not GENERATED.match(Path(stock.image.name).name):
                continue  # kullanıcının kendi fotoğrafı
            stock.image.save(f"stock-{stock.pk}.jpg", ContentFile(make_image(stock)), save=True)  # eski dosyayı model siler
            count += 1
        self.stdout.write(self.style.SUCCESS(f"{count} stok kaydına örnek görsel eklendi."))
