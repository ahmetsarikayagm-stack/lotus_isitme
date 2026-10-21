"""Ay Sonu PDF raporları (A4 yatay): logolu antet, alt bilgide firma bilgileri ve sayfa numarası.

Yıllık ve aylık rapor AYNI biçimdedir: Kira, Elektrik, Su, İnternet, Maaş, Muhasebe, Genel Gid.,
Cihaz Gid., Top. Gid., Top. Gel., Kâr. Yıllıkta 12 ay + toplam, aylıkta o ayın tek satırı vardır.
"""
import io
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape as esc

import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.platypus.flowables import HRFlowable

from .reports import LOGO_WHITE, company_info

# ---------------------------------------------------------------- sabitler
PAGE_W, PAGE_H = landscape(A4)
MARGIN = 18 * mm
CONTENT_W = PAGE_W - 2 * MARGIN
BAND_H = 28 * mm
FOOTER_H = 23 * mm

BRAND = colors.HexColor("#EF7B18")
BRAND_DARK = colors.HexColor("#B4510C")
BRAND_LIGHT = colors.HexColor("#FEF4EA")
INK = colors.HexColor("#0F172A")
MUTED = colors.HexColor("#64748B")
LINE = colors.HexColor("#E2E8F0")
PANEL = colors.HexColor("#F8FAFC")
GREEN_HEX, RED_HEX, GREY_HEX = "#059669", "#DC2626", "#94A3B8"

# Rapor tablosu: sütun başlıkları ve genişlikleri (mm) — toplam 261 mm
HEADERS = ["Ay", "Kira", "Elektrik", "Su", "İnternet", "Maaş", "Muhasebe", "Genel Gid.", "Cihaz Gid.", "Top. Gid.", "Top. Gel.", "Kâr"]
WIDTHS_MM = [21, 20, 20, 16, 19, 21, 20, 21, 24, 25, 25, 29]

FONT_DIR = Path(__file__).resolve().parent / "fonts"
_fonts = {}


def _register_fonts():
    """Türkçe karakterleri destekleyen yazı tipi: önce paketlenmiş Carlito, olmazsa ReportLab'in Vera'sı."""
    if _fonts:
        return _fonts["regular"], _fonts["bold"]
    rl_fonts = Path(reportlab.__file__).resolve().parent / "fonts"
    for regular, bold in ((FONT_DIR / "Carlito-Regular.ttf", FONT_DIR / "Carlito-Bold.ttf"),
                          (rl_fonts / "Vera.ttf", rl_fonts / "VeraBd.ttf")):
        if regular.exists() and bold.exists():
            pdfmetrics.registerFont(TTFont("LotusSans", str(regular)))
            pdfmetrics.registerFont(TTFont("LotusSans-Bold", str(bold)))
            pdfmetrics.registerFontFamily("LotusSans", normal="LotusSans", bold="LotusSans-Bold",
                                          italic="LotusSans", boldItalic="LotusSans-Bold")
            _fonts.update(regular="LotusSans", bold="LotusSans-Bold")
            return "LotusSans", "LotusSans-Bold"
    raise RuntimeError("Rapor için yazı tipi bulunamadı (apps/month_end/fonts).")


# ---------------------------------------------------------------- biçimlendirme
def num(value, digits=2) -> str:
    s = f"{float(value or 0):,.{digits}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def tl(value) -> str:
    return num(value) + " TL"  # yazı tipinde ₺ simgesi olmadığı için TL


def pct(value) -> str:
    return "—" if value is None else f"%{value:.1f}".replace(".", ",")


def _profit_html(value, bold=True, money=True) -> str:
    color = GREEN_HEX if float(value) >= 0 else RED_HEX
    text = tl(value) if money else num(value)
    return f'<font color="{color}"><b>{text}</b></font>' if bold else f'<font color="{color}">{text}</font>'


# ---------------------------------------------------------------- stiller
def _styles():
    reg, bold = _register_fonts()
    S = lambda name, **kw: ParagraphStyle(name, fontName=kw.pop("fontName", reg), **kw)
    return {
        "title": S("title", fontName=bold, fontSize=21, leading=24, textColor=INK),
        "period": S("period", fontName=bold, fontSize=15, leading=19, textColor=BRAND),
        "meta": S("meta", fontSize=8.5, leading=11, textColor=MUTED),
        "h2": S("h2", fontName=bold, fontSize=11.5, leading=14, textColor=INK, spaceBefore=9, spaceAfter=2, keepWithNext=1),
        "kpi_label": S("kpi_label", fontSize=8, leading=10, textColor=MUTED),
        "kpi_value": S("kpi_value", fontName=bold, fontSize=14.5, leading=18, textColor=INK, spaceBefore=1),
        "head": S("head", fontName=bold, fontSize=8.3, leading=10, textColor=colors.white),
        "head_r": S("head_r", fontName=bold, fontSize=8.3, leading=10, textColor=colors.white, alignment=TA_RIGHT),
        "cell_b": S("cell_b", fontName=bold, fontSize=8.8, leading=11, textColor=INK),
        "num": S("num", fontSize=8.4, leading=11, textColor=INK, alignment=TA_RIGHT),
        "num_b": S("num_b", fontName=bold, fontSize=8.4, leading=11, textColor=INK, alignment=TA_RIGHT),
        "small": S("small", fontSize=8, leading=10.5, textColor=INK),
        "small_r": S("small_r", fontSize=8, leading=10.5, textColor=INK, alignment=TA_RIGHT),
        "small_rb": S("small_rb", fontName=bold, fontSize=8, leading=10.5, textColor=INK, alignment=TA_RIGHT),
        "small_b": S("small_b", fontName=bold, fontSize=8, leading=10.5, textColor=INK),
        "note": S("note", fontSize=8, leading=10.5, textColor=MUTED),
        "empty": S("empty", fontSize=8.4, leading=11, textColor=MUTED, alignment=TA_CENTER),
    }


# ---------------------------------------------------------------- antet + alt bilgi
def _draw_letterhead(canv, doc):
    reg, bold = _register_fonts()
    info = company_info()
    canv.saveState()
    canv.setFillColor(BRAND)
    canv.rect(0, PAGE_H - BAND_H, PAGE_W, BAND_H, stroke=0, fill=1)
    canv.setFillColor(BRAND_DARK)
    canv.rect(0, PAGE_H - BAND_H - 1.3 * mm, PAGE_W, 1.3 * mm, stroke=0, fill=1)

    logo_h = BAND_H - 7 * mm
    iw, ih = ImageReader(str(LOGO_WHITE)).getSize()
    canv.drawImage(str(LOGO_WHITE), MARGIN, PAGE_H - BAND_H + 3.5 * mm, width=logo_h * iw / ih, height=logo_h,
                   mask="auto", preserveAspectRatio=True)

    canv.setFillColor(colors.white)
    canv.setFont(bold, 17)
    canv.drawRightString(PAGE_W - MARGIN, PAGE_H - BAND_H / 2 - 2 * mm, info["name"])
    canv.restoreState()


def _canvas_class(prepared_by):
    """Alt bilgi için iki geçişli canvas (sayfa x / y); her rapora özel sınıf (iş parçacığı güvenli)."""
    reg, _ = _register_fonts()
    info = company_info()
    contact = "  ·  ".join(x for x in (info["phone"], info["email"]) if x)
    stamp = f"Hazırlayan: {prepared_by}  ·  {datetime.now():%d.%m.%Y %H:%M}"

    class NumberedCanvas(rl_canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._saved_pages = []

        def showPage(self):
            self._saved_pages.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._saved_pages)
            for state in self._saved_pages:
                self.__dict__.update(state)
                self._draw_footer(total)
                super().showPage()
            super().save()

        def _draw_footer(self, total):
            self.saveState()
            self.setStrokeColor(LINE)
            self.setLineWidth(0.6)
            self.line(MARGIN, 17 * mm, PAGE_W - MARGIN, 17 * mm)
            self.setFillColor(MUTED)
            self.setFont(reg, 8.3)
            self.drawString(MARGIN, 12.5 * mm, info["address"])          # adres
            self.drawString(MARGIN, 8.3 * mm, contact)                    # telefon · e-posta
            self.drawRightString(PAGE_W - MARGIN, 12.5 * mm, f"Sayfa {self._pageNumber} / {total}")
            self.drawRightString(PAGE_W - MARGIN, 8.3 * mm, stamp)
            self.restoreState()

    return NumberedCanvas


def _build(story, title, prepared_by) -> bytes:
    buf = io.BytesIO()
    info = company_info()
    doc = BaseDocTemplate(buf, pagesize=landscape(A4), leftMargin=MARGIN, rightMargin=MARGIN,
                          topMargin=BAND_H + 8 * mm, bottomMargin=FOOTER_H, title=title, author=info["name"],
                          creator="Lotus İşitme Yönetim Sistemi")
    frame = Frame(MARGIN, FOOTER_H, CONTENT_W, PAGE_H - BAND_H - 8 * mm - FOOTER_H, id="body",
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=_draw_letterhead)])
    doc.build(story, canvasmaker=_canvas_class(prepared_by))
    return buf.getvalue()


# ---------------------------------------------------------------- ortak bileşenler
def _heading(text, st):
    """Bölüm başlığı; sonraki içerikle birlikte kalır (sayfa sonunda tek başına kalmaz)."""
    rule = HRFlowable(width="100%", thickness=1, color=BRAND, spaceAfter=5)
    rule.keepWithNext = 1
    return [Paragraph(text, st["h2"]), rule]


def _title_block(st, title, period, prepared_by, status_html=None):
    block = [
        Paragraph(title, st["title"]),
        Paragraph(period, st["period"]),
        Spacer(1, 1),
        Paragraph(f"Rapor tarihi: {datetime.now():%d.%m.%Y %H:%M}  ·  Hazırlayan: {esc(prepared_by)}", st["meta"]),
    ]
    if status_html:
        block += [Spacer(1, 2), Paragraph(status_html, st["meta"])]
    return block + [Spacer(1, 7)]


def period_status_html(me) -> str:
    """Dönem açık / kapalı bilgisi (rapor başlığında)."""
    if me.is_closed:
        who = f" · {esc(me.closed_by.display_name)}" if me.closed_by else ""
        when = f"{me.closed_at:%d.%m.%Y %H:%M}" if me.closed_at else ""
        return (f'<font color="#0F172A"><b>KAPALI DÖNEM</b></font> — {when}{who} tarafından kapatılmıştır; '
                "değerler dondurulmuştur.")
    return "Dönem açıktır; değerler güncel satışlara göre hesaplanmıştır."


def _kpi_table(st, income, expense, profit):
    margin = (profit / income * 100) if income else None
    cell = lambda label, value: [Paragraph(label, st["kpi_label"]), Paragraph(value, st["kpi_value"])]
    t = Table([[cell("TOPLAM GELİR", tl(income)), cell("TOPLAM GİDER", tl(expense)),
                cell("NET KÂR / ZARAR", _profit_html(profit)), cell("KÂR MARJI", pct(margin))]],
              colWidths=[CONTENT_W / 4] * 4)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PANEL), ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.6, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def _grid(rows, widths, header=True, zebra=True, extra=None, repeat=0, pad=5):
    t = Table(rows, colWidths=widths, repeatRows=repeat)
    style = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), pad), ("BOTTOMPADDING", (0, 0), (-1, -1), pad),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
    ]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), BRAND_DARK))
    if zebra:
        style.append(("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, PANEL]))
    t.setStyle(TableStyle(style + (extra or [])))
    return t


def _values(m):
    """Tablo sırası: Kira, Elektrik, Su, İnternet, Maaş, Muhasebe, Genel Gid., Cihaz Gid., Top. Gid., Top. Gel., Kâr."""
    return [m.rent, m.electricity, m.water, m.internet, m.salary, m.accounting, m.general_expenses,
            m.device_cost, m.total_expense, m.total_income, m.profit]


def _expense_table(st, rows, with_total):
    """Yıllık ve aylık raporun ortak tablosu. rows: [{"name": "Eylül", "obj": MonthEnd | None}, ...]"""
    head = [Paragraph(h, st["head"] if i == 0 else st["head_r"]) for i, h in enumerate(HEADERS)]
    body = [head]
    spans = []
    for r in rows:
        m = r["obj"]
        if m is None:
            body.append([Paragraph(f'<font color="{GREY_HEX}">{r["name"]}</font>', st["cell_b"]),
                         Paragraph(f'<font color="{GREY_HEX}">kayıt yok</font>', st["empty"])] + [""] * 10)
            spans.append(("SPAN", (1, len(body) - 1), (-1, len(body) - 1)))
            continue
        cells = [Paragraph(r["name"], st["cell_b"])]
        for i, v in enumerate(_values(m)):
            if i == 10:                                           # Kâr: yeşil / kırmızı
                cells.append(Paragraph(_profit_html(v, money=False), st["num_b"]))
            else:
                cells.append(Paragraph(num(v), st["num_b"] if i in (8, 9) else st["num"]))
        body.append(cells)
    extra = list(spans)
    if with_total:
        recs = [r["obj"] for r in rows if r["obj"]]
        totals = [sum(float(_values(m)[i]) for m in recs) for i in range(11)]
        body.append([Paragraph("TOPLAM", st["cell_b"])] + [
            Paragraph(_profit_html(v, money=False) if i == 10 else num(v), st["num_b"]) for i, v in enumerate(totals)])
        n = len(body) - 1
        extra += [("BACKGROUND", (0, n), (-1, n), BRAND_LIGHT), ("LINEABOVE", (0, n), (-1, n), 1, INK)]
    return _grid(body, [w * mm for w in WIDTHS_MM], extra=extra, repeat=1, pad=3)   # 12 ay + toplam tek sayfaya sığsın


NOTE = ("Tutarlar TL cinsindendir. Top. Gid. = Kira + Elektrik + Su + İnternet + Maaş + Muhasebe + Genel Gid. + Cihaz Gid.;  "
        "Kâr = Top. Gel. − Top. Gid.")


# ================================================================= YILLIK RAPOR
def build_year_pdf(data: dict, prepared_by: str = "") -> bytes:
    st = _styles()
    year, rows = data["year"], data["rows"]
    recs = [r["obj"] for r in rows if r["obj"]]
    income = sum(float(m.total_income) for m in recs)
    expense = sum(float(m.total_expense) for m in recs)

    story = _title_block(st, "Yıllık Ay Sonu Raporu", str(year), prepared_by)
    story.append(_kpi_table(st, income, expense, income - expense))
    story += _heading("Aylık Döküm", st)
    story.append(_expense_table(st, rows, with_total=True))
    story.append(Paragraph(NOTE + " Ay sonu kaydı girilmemiş aylar toplamlara dahil değildir.", st["note"]))
    return _build(story, f"Yıllık Ay Sonu Raporu – {year}", prepared_by)


# ================================================================= AYLIK RAPOR (yıllıkla aynı biçim)
def build_month_pdf(data: dict, prepared_by: str = "") -> bytes:
    st = _styles()
    me = data["me"]

    story = _title_block(st, "Ay Sonu Raporu", me.period_label, prepared_by, period_status_html(me))
    story.append(_kpi_table(st, float(me.total_income), float(me.total_expense), float(me.profit)))
    story += _heading("Dönem Dökümü", st)
    story.append(_expense_table(st, [{"name": me.get_month_display(), "obj": me}], with_total=False))
    story.append(Paragraph(NOTE, st["note"]))

    # --- ek: bu aya ait satışlar
    if data["sales"]:
        story += [Spacer(1, 6)] + _heading("Ek: Satış Listesi", st)
        rows = [[Paragraph("Tarih", st["head"]), Paragraph("Hasta", st["head"]), Paragraph("Ürünler", st["head"]),
                 Paragraph("Ödeme", st["head"]), Paragraph("Toplam", st["head_r"]), Paragraph("Kapora", st["head_r"]),
                 Paragraph("Kalan", st["head_r"])]]
        for sale in data["sales"]:
            parts = [f"{i.product}" + (f" ×{i.quantity}" if i.quantity > 1 else "") for i in sale.items.all()]
            rows.append([Paragraph(f"{sale.sale_date:%d.%m.%Y}", st["small"]), Paragraph(esc(str(sale.patient)), st["small"]),
                         Paragraph(esc(" + ".join(parts)), st["small"]), Paragraph(esc(sale.payment_method.name), st["small"]),
                         Paragraph(num(sale.total), st["small_r"]), Paragraph(num(sale.deposit), st["small_r"]),
                         Paragraph(num(sale.remaining), st["small_r"])])
        tot = lambda f: sum(float(getattr(x, f)) for x in data["sales"])
        rows.append([Paragraph("TOPLAM", st["small_b"]), "", "", "", Paragraph(num(tot("total")), st["small_rb"]),
                     Paragraph(num(tot("deposit")), st["small_rb"]), Paragraph(num(tot("remaining")), st["small_rb"])])
        n = len(rows) - 1
        widths = [mm * w for w in (22, 48, 100, 26, 25, 20, 20)]
        story.append(_grid(rows, widths, repeat=1, extra=[
            ("BACKGROUND", (0, n), (-1, n), BRAND_LIGHT), ("LINEABOVE", (0, n), (-1, n), 1, INK),
            ("SPAN", (0, n), (3, n)), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story.append(Paragraph("Satış tutarları indirim düşülmüş net tutarlardır.", st["note"]))

    return _build(story, f"Ay Sonu Raporu – {me.period_label}", prepared_by)
