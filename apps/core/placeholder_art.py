"""Örnek veri için yer tutucu marka logosu ve renkleri (gerçek marka logolarını TAKLİT ETMEZ)."""
import io
import zlib
from pathlib import Path

from django.conf import settings
from PIL import Image, ImageDraw, ImageFont

# marka: (açık zemin, vurgu rengi) — renkler örnektir
BRAND_COLORS = {
    "Phonak": ("#FDE6CF", "#EF7B18"), "Oticon": ("#DBEAFE", "#2563EB"), "Signia": ("#DCFCE7", "#16A34A"),
    "Widex": ("#EDE9FE", "#7C3AED"), "ReSound": ("#FCE7F3", "#DB2777"), "Rayovac": ("#FEF9C3", "#B45309"),
}
_FALLBACK = [("#E0F2FE", "#0284C7"), ("#CCFBF1", "#0F766E"), ("#F3E8FF", "#9333EA"), ("#FEE2E2", "#DC2626"), ("#E2E8F0", "#475569")]

FONT_BOLD = Path(settings.BASE_DIR) / "apps" / "month_end" / "fonts" / "Carlito-Bold.ttf"


def colors_for(name: str) -> tuple[str, str]:
    """Bilinen markaya sabit, bilinmeyene ada göre tutarlı bir renk çifti."""
    return BRAND_COLORS.get(name) or _FALLBACK[zlib.crc32(name.encode("utf-8")) % len(_FALLBACK)]


def _font(size):
    try:
        return ImageFont.truetype(str(FONT_BOLD), size)
    except OSError:
        try:
            return ImageFont.load_default(size=size)
        except TypeError:
            return ImageFont.load_default()


def make_brand_logo(name: str) -> bytes:
    """Marka adını yazan, yuvarlatılmış köşeli, şeffaf zeminli yer tutucu rozet (PNG)."""
    width, height = 480, 200
    _, accent = colors_for(name)
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=40, fill=accent)
    size = 104
    while size > 24:                      # uzun adlar sığana kadar küçült
        font = _font(size)
        left, top, right, bottom = draw.textbbox((0, 0), name, font=font)
        if right - left <= width - 70:
            break
        size -= 4
    draw.text(((width - (right - left)) / 2 - left, (height - (bottom - top)) / 2 - top), name, font=font, fill="white")
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()
