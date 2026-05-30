"""
Simak Fresh — Unified Receipt Suite
────────────────────────────────────
render_receipt_image()      PIL image receipt  (lightweight, thumbnail-grade)
render_receipt_pdf()        Standard customer PDF receipt
render_admin_receipt_pdf()  Full admin PDF receipt with QR, summary, address

Design rules
  • Dark header band snaps tightly around content — no blank padding top/bottom
  • Logo and company details sit at the same vertical midpoint
  • Greyscale-safe: hierarchy conveyed by weight/shape, not colour alone
  • Logo black background stripped via NumPy before embedding
"""

from io import BytesIO
from datetime import datetime, date
from decimal import Decimal
import os

import qrcode
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader


# ══════════════════════════════════════════════════════════════════════════════
#  SHARED PALETTE  (greyscale-safe)
# ══════════════════════════════════════════════════════════════════════════════
DARK_BG   = HexColor("#111111")   # header band      → prints solid black
PRIMARY   = HexColor("#1A1A1A")   # table hdr / rule → prints black
RULE_STR  = HexColor("#555555")   # dividers          → prints dark grey
ROW_ALT   = HexColor("#EEEEEE")   # alternate rows    → prints light grey
TEXT      = HexColor("#111111")   # body text         → prints black
MUTED     = HexColor("#444444")   # labels / captions → prints dark grey
WHITE_COL = HexColor("#FFFFFF")
TEAL_ACC  = HexColor("#1DB8B8")   # thin accent stripe
CORAL_ACC = HexColor("#E8433A")   # thin accent stripe

# ── Header geometry ───────────────────────────────────────────────────────────
LOGO_H    = 42 * mm
LOGO_W    = 86 * mm
STR_T     = 2.5 * mm
STR_B     = 1.5 * mm
PAD_V     = 4 * mm
HEADER_H  = STR_T + PAD_V + LOGO_H + PAD_V + STR_B   # ≈ 54 mm

ML = 15 * mm
MR = 15 * mm
FOOTER_H = 18 * mm

# Website brand palette (customer PDF receipt only)
BRAND_NAVY       = HexColor("#002b36")
BRAND_TEAL       = HexColor("#008CBA")
BRAND_TEAL_LIGHT = HexColor("#00a8b5")
BRAND_YELLOW     = HexColor("#F5B800")
BRAND_WHITE      = HexColor("#FFFFFF")
BRAND_BODY_BG    = HexColor("#F7FAFB")
BRAND_TEXT       = HexColor("#002b36")
BRAND_MUTED      = HexColor("#5A7A85")
BRAND_ROW_ALT    = HexColor("#E8F4F8")

PDF_LOGO_H = 34 * mm
PDF_LOGO_W = 68 * mm
PDF_HEADER_H = 58 * mm
PDF_THANK_Y = FOOTER_H + 7 * mm
BRAND_PHONE = "+971 545 446 111"
BRAND_EMAIL = "support@simakfresh.ae"
BRAND_MOTTO = "LIVE SEAFOOD FROM SEA TO HOME"
BRAND_ADDRESS_LINES = (
    "Sharjah Media City, Sharjah, UAE",
    "Mushrif Mall - Abu Dhabi, UAE",
)

# Lucide icons (same stroke style as website footer)
_LUCIDE_PHONE_PATH = (
    "M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 "
    "19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 "
    "2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 "
    "6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"
)
_LUCIDE_MAP_PIN_PATH = (
    "M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 "
    "4 14.993 4 10a8 8 0 0 1 16 0"
)
_LUCIDE_MAP_PIN_DOT = "M12 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"
_PATH_OP_ARGS = (2, 2, 6, 0)


# ══════════════════════════════════════════════════════════════════════════════
#  LOGO HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _default_pdf_logo_path() -> str:
    from django.conf import settings
    branding_logo = os.path.join(settings.MEDIA_ROOT, "branding", "email_logo.png")
    if os.path.isfile(branding_logo):
        return branding_logo
    configured = getattr(settings, "EMAIL_LOGO_PATH", None)
    if configured and os.path.isfile(configured):
        return configured
    return branding_logo


def _pdf_payment_method_label(payment) -> str:
    """Customer-facing label — card gateway payments show as Card, not provider name."""
    if not payment:
        return "Card"
    if payment.payment_method == "COD":
        return "Cash on Delivery"
    return "Card"


def _prepare_logo(logo_path: str):
    """Remove solid-black background → transparent PNG for use on dark band."""
    try:
        img  = Image.open(logo_path).convert("RGBA")
        data = np.array(img, dtype=np.uint8)
        r, g, b = data[:, :, 0], data[:, :, 1], data[:, :, 2]
        data[(r < 55) & (g < 55) & (b < 55), 3] = 0
        buf = BytesIO()
        Image.fromarray(data, "RGBA").save(buf, format="PNG")
        buf.seek(0)
        return ImageReader(buf)
    except Exception as e:
        print(f"[logo] {e}")
        return None


def _prepare_logo_pdf(logo_path: str):
    """Remove near-white background so the colourful logo sits on the navy header."""
    try:
        img = Image.open(logo_path).convert("RGBA")
        data = np.array(img, dtype=np.uint8)
        r, g, b = data[:, :, 0], data[:, :, 1], data[:, :, 2]
        near_white = (r > 235) & (g > 235) & (b > 235)
        data[near_white, 3] = 0
        buf = BytesIO()
        Image.fromarray(data, "RGBA").save(buf, format="PNG")
        buf.seek(0)
        return ImageReader(buf)
    except Exception as e:
        print(f"[logo-pdf] {e}")
        return None


def _prepare_logo_pil(logo_path: str):
    """Return PIL RGBA image with black background stripped (for image receipts)."""
    try:
        img  = Image.open(logo_path).convert("RGBA")
        data = np.array(img, dtype=np.uint8)
        r, g, b = data[:, :, 0], data[:, :, 1], data[:, :, 2]
        data[(r < 55) & (g < 55) & (b < 55), 3] = 0
        return Image.fromarray(data, "RGBA")
    except:
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  PDF DRAWING PRIMITIVES
# ══════════════════════════════════════════════════════════════════════════════
def _rrect(pdf, x, y, w, h, r=2*mm, fill=None, stroke=None, lw=0.6):
    pdf.saveState()
    if fill:   pdf.setFillColor(fill)
    if stroke: pdf.setStrokeColor(stroke); pdf.setLineWidth(lw)
    pdf.roundRect(x, y, w, h, r,
                  fill=1 if fill else 0,
                  stroke=1 if stroke else 0)
    pdf.restoreState()


def _section(pdf, x, y, label, sw=170*mm):
    """Solid-black accent bar + bold label + thin rule — greyscale safe."""
    pdf.saveState()
    pdf.setFillColor(PRIMARY)
    pdf.rect(x, y - 3.8*mm, 3*mm, 5.5*mm, fill=1, stroke=0)
    pdf.setFont("Helvetica-Bold", 8.5)
    pdf.setFillColor(PRIMARY)
    pdf.drawString(x + 5*mm, y - 0.2*mm, label.upper())
    pdf.setStrokeColor(RULE_STR); pdf.setLineWidth(0.4)
    pdf.line(x + 5*mm + len(label)*5.4 + 2*mm, y - 0.2*mm, x + sw, y - 0.2*mm)
    pdf.restoreState()
    return y - 6.5*mm


def _kv(pdf, x, y, key, val, kw=17*mm, fs=8):
    pdf.saveState()
    pdf.setFont("Helvetica-Bold", fs); pdf.setFillColor(MUTED)
    pdf.drawString(x, y, key)
    pdf.setFont("Helvetica", fs);      pdf.setFillColor(TEXT)
    pdf.drawString(x + kw, y, val)
    pdf.restoreState()
    return y - (fs * 0.45*mm + 1.4*mm)


def _make_qr(data: str) -> ImageReader:
    qr = qrcode.QRCode(version=1, box_size=8, border=3,
                       error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


# ══════════════════════════════════════════════════════════════════════════════
#  SHARED HEADER
# ══════════════════════════════════════════════════════════════════════════════
def _draw_header(pdf, width, height, logo_reader, compact=False):
    pdf.setFillColor(DARK_BG)
    pdf.rect(0, height - HEADER_H, width, HEADER_H, fill=1, stroke=0)

    pdf.setFillColor(TEAL_ACC)
    pdf.rect(0, height - STR_T, width, STR_T, fill=1, stroke=0)

    pdf.setFillColor(CORAL_ACC)
    pdf.rect(0, height - HEADER_H, width, STR_B, fill=1, stroke=0)

    logo_y = height - HEADER_H + STR_B + PAD_V
    if logo_reader:
        pdf.drawImage(logo_reader, ML, logo_y,
                      width=LOGO_W, height=LOGO_H,
                      preserveAspectRatio=True, mask='auto')

    if compact:
        return

    TEXT_BLOCK_H = 4.5 + 3 * 4.5
    logo_mid     = logo_y + LOGO_H / 2
    blk_top      = logo_mid + TEXT_BLOCK_H / 2

    rx = width - MR
    cy = blk_top

    pdf.setFont("Helvetica-Bold", 13)
    pdf.setFillColor(WHITE_COL)
    pdf.drawRightString(rx, cy, "SIMAK FRESH LLC")

    pdf.setFont("Helvetica", 9)
    pdf.setFillColor(HexColor("#CCCCCC"))
    for line in [
        "Sharjah Media City, Sharjah, UAE",
        "Mushif Mall, Abu Dhabi, UAE",
        "www.simakfresh.ae  |  +971 54 54 46 111",
    ]:
        cy -= 4.5*mm
        pdf.drawRightString(rx, cy, line)


# ══════════════════════════════════════════════════════════════════════════════
#  SHARED FOOTER
# ══════════════════════════════════════════════════════════════════════════════
def _draw_footer(pdf, width, page_num, total_pages, ref, generated_at):
    y = FOOTER_H
    pdf.setStrokeColor(RULE_STR); pdf.setLineWidth(0.5)
    pdf.line(ML, y, width - MR, y)
    pdf.setFont("Helvetica", 6.5); pdf.setFillColor(MUTED)
    pdf.drawString(ML, y - 4*mm,
        f"Generated: {generated_at}  |  Ref: {ref}  |  "
        "Thank you for choosing Simak Fresh — Signature of Quality")
    pdf.drawRightString(width - MR, y - 4*mm, f"Page {page_num} of {total_pages}")


# ══════════════════════════════════════════════════════════════════════════════
#  STATUS BADGE
# ══════════════════════════════════════════════════════════════════════════════
_STATUS_MAP = {
    "Delivered":  "DELIVERED",
    "Pending":    "PENDING",
    "Cancelled":  "CANCELLED",
    "Processing": "PROCESSING",
    "Confirmed":  "CONFIRMED",
}


def _badge(pdf, rx, y, status):
    label    = _STATUS_MAP.get(status, status.upper())
    badge_w  = (len(label) * 4.6 + 14) * mm / mm
    bx       = rx - badge_w * mm
    terminal = status in ("Delivered", "Cancelled")
    if terminal:
        _rrect(pdf, bx, y - 5.5*mm, badge_w*mm, 7.5*mm, r=2*mm, fill=PRIMARY)
        pdf.setFont("Helvetica-Bold", 7.5); pdf.setFillColor(WHITE_COL)
    else:
        _rrect(pdf, bx, y - 5.5*mm, badge_w*mm, 7.5*mm, r=2*mm, stroke=PRIMARY, lw=1.4)
        pdf.setFont("Helvetica-Bold", 7.5); pdf.setFillColor(PRIMARY)
    pdf.drawCentredString(bx + badge_w*mm / 2, y - 1.8*mm, label)


# ══════════════════════════════════════════════════════════════════════════════
#  TABLE HEADER ROW
# ══════════════════════════════════════════════════════════════════════════════
def _tbl_hdr(pdf, y, TABLE_W, COL, width):
    _rrect(pdf, ML, y - 7*mm, TABLE_W, 7.5*mm, r=1.5*mm, fill=PRIMARY)
    pdf.setFont("Helvetica-Bold", 8); pdf.setFillColor(WHITE_COL)
    pdf.drawString(COL['name'] + 2*mm,         y - 5*mm, "Product / Description")
    pdf.drawCentredString(COL['qty'] + 10*mm,  y - 5*mm, "Qty")
    pdf.drawString(COL['price'],               y - 5*mm, "Unit Price")
    pdf.drawRightString(COL['sub'] - 1*mm,     y - 5*mm, "Subtotal")
    return y - 9*mm


# ══════════════════════════════════════════════════════════════════════════════
#  BRANDED PDF RECEIPT (customer payment PDF only)
# ══════════════════════════════════════════════════════════════════════════════
def _canvas_draw_svg_path(pdf, cx, cy, size, path_d, color, stroke_w=1.6):
    """Draw Lucide SVG path (24×24 viewBox) centred at cx,cy — matches website footer icons."""
    from reportlab.graphics.svgpath import SvgPath

    sp = SvgPath(path_d)
    scale = size / 24.0
    pdf.saveState()
    # SVG Y-axis points down; PDF Y-axis points up — flip so icons are upright.
    pdf.translate(cx, cy)
    pdf.scale(scale, -scale)
    pdf.translate(-12, -12)
    pdf.setStrokeColor(color)
    pdf.setLineWidth(stroke_w / scale)
    pdf.setLineCap(1)
    pdf.setLineJoin(1)

    p = pdf.beginPath()
    pts = sp.points
    i = 0
    for op in sp.operators:
        n = _PATH_OP_ARGS[op]
        chunk = pts[i : i + n]
        i += n
        if op == 0:
            p.moveTo(chunk[0], chunk[1])
        elif op == 1:
            p.lineTo(chunk[0], chunk[1])
        elif op == 2:
            p.curveTo(chunk[0], chunk[1], chunk[2], chunk[3], chunk[4], chunk[5])
        elif op == 3:
            p.close()
    pdf.drawPath(p, stroke=1, fill=0)
    pdf.restoreState()


def _draw_footer_phone_icon(pdf, cx, cy, size, color):
    _canvas_draw_svg_path(pdf, cx, cy, size, _LUCIDE_PHONE_PATH, color)


def _draw_footer_map_pin_icon(pdf, cx, cy, size, color):
    _canvas_draw_svg_path(pdf, cx, cy, size, _LUCIDE_MAP_PIN_PATH, color)
    _canvas_draw_svg_path(pdf, cx, cy, size, _LUCIDE_MAP_PIN_DOT, color)


def _pdf_draw_right_icon_line(
    pdf, rx, y, text, icon_kind, font="Helvetica", fs=8, color=None, icon_size=3.4 * mm,
):
    color = color or BRAND_TEAL_LIGHT
    pdf.setFont(font, fs)
    tw = pdf.stringWidth(text, font, fs)
    gap = 2.2 * mm
    icon_cx = rx - tw - gap - icon_size / 2
    icon_cy = y + fs * 0.35
    if icon_kind == "phone":
        _draw_footer_phone_icon(pdf, icon_cx, icon_cy, icon_size, color)
    elif icon_kind == "map-pin":
        _draw_footer_map_pin_icon(pdf, icon_cx, icon_cy, icon_size, color)
    pdf.setFillColor(color)
    pdf.drawRightString(rx, y, text)


def _draw_pdf_header(pdf, width, height, logo_reader, compact=False):
    pdf.setFillColor(BRAND_NAVY)
    pdf.rect(0, height - PDF_HEADER_H, width, PDF_HEADER_H, fill=1, stroke=0)
    pdf.setFillColor(BRAND_TEAL)
    pdf.rect(0, height - 2 * mm, width, 2 * mm, fill=1, stroke=0)

    logo_y = height - PDF_HEADER_H + 7 * mm
    if logo_reader:
        pdf.drawImage(
            logo_reader, ML, logo_y,
            width=PDF_LOGO_W, height=PDF_LOGO_H,
            preserveAspectRatio=True, mask="auto",
        )

    if compact:
        return

    rx = width - MR
    cy = logo_y + PDF_LOGO_H - 2 * mm
    pdf.setFont("Helvetica-Bold", 14)
    pdf.setFillColor(BRAND_WHITE)
    pdf.drawRightString(rx, cy, "SIMAK FRESH")
    cy -= 4.5 * mm
    _pdf_draw_right_icon_line(
        pdf, rx, cy, BRAND_PHONE, "phone",
        font="Helvetica", fs=8, color=BRAND_TEAL_LIGHT,
    )
    cy -= 4 * mm
    addr_color = HexColor("#D8EEF2")
    for line in BRAND_ADDRESS_LINES:
        _pdf_draw_right_icon_line(
            pdf, rx, cy, line, "map-pin",
            font="Helvetica", fs=7, color=addr_color,
        )
        cy -= 3.8 * mm
    cy -= 1 * mm
    pdf.setFont("Helvetica-Bold", 7.5)
    pdf.setFillColor(BRAND_YELLOW)
    pdf.drawRightString(rx, cy, BRAND_MOTTO)


def _draw_pdf_thank_you(pdf, width):
    """Fixed position just above the footer band."""
    pdf.setFont("Helvetica-Oblique", 7.5)
    pdf.setFillColor(BRAND_MUTED)
    pdf.drawCentredString(
        width / 2,
        PDF_THANK_Y,
        "Thank you for choosing Simak Fresh  |  100% Secure Payments",
    )


def _draw_pdf_footer(pdf, width, page_num, total_pages, ref, generated_at):
    band_h = FOOTER_H + 2 * mm
    pdf.setFillColor(BRAND_NAVY)
    pdf.rect(0, 0, width, band_h, fill=1, stroke=0)
    pdf.setFillColor(BRAND_TEAL)
    pdf.rect(0, band_h - 1.2 * mm, width, 1.2 * mm, fill=1, stroke=0)

    y = band_h - 5 * mm
    pdf.setFont("Helvetica-Bold", 6.5)
    pdf.setFillColor(BRAND_YELLOW)
    pdf.drawString(ML, y, BRAND_MOTTO)
    pdf.setFont("Helvetica", 6.5)
    pdf.setFillColor(BRAND_TEAL_LIGHT)
    pdf.drawRightString(width - MR, y, f"Page {page_num} of {total_pages}")

    y -= 4 * mm
    pdf.setFillColor(BRAND_WHITE)
    pdf.drawString(ML, y, f"{BRAND_EMAIL}  |  {BRAND_PHONE}")
    pdf.drawRightString(
        width - MR, y,
        f"Ref {ref}  |  {generated_at}",
    )


def _pdf_section(pdf, x, y, label, sw=170 * mm):
    pdf.setFillColor(BRAND_TEAL)
    pdf.rect(x, y - 3.8 * mm, 3 * mm, 5.5 * mm, fill=1, stroke=0)
    pdf.setFont("Helvetica-Bold", 8.5)
    pdf.setFillColor(BRAND_NAVY)
    pdf.drawString(x + 5 * mm, y - 0.2 * mm, label.upper())
    pdf.setStrokeColor(HexColor("#B8D4DE"))
    pdf.setLineWidth(0.4)
    pdf.line(x + 5 * mm + len(label) * 5.4 + 2 * mm, y - 0.2 * mm, x + sw, y - 0.2 * mm)
    return y - 6.5 * mm


def _pdf_kv(pdf, x, y, key, val, label_w=24 * mm, fs=8, val_max_chars=42):
    pdf.setFont("Helvetica-Bold", fs)
    pdf.setFillColor(BRAND_MUTED)
    pdf.drawString(x, y, key)
    pdf.setFont("Helvetica", fs)
    pdf.setFillColor(BRAND_TEXT)
    pdf.drawString(x + label_w, y, str(val)[:val_max_chars])
    return y - 4.2 * mm


def _pdf_table_layout(left, right):
    """Column positions derived from table edges so headers and rows align."""
    tw = right - left
    qty_w, unit_w, sub_w = 18 * mm, 32 * mm, 30 * mm
    name_w = tw - qty_w - unit_w - sub_w
    return {
        "left": left,
        "right": right,
        "tw": tw,
        "name_x": left + 2 * mm,
        "name_end": left + name_w,
        "qty_cx": left + name_w + qty_w / 2,
        "unit_rx": left + name_w + qty_w + unit_w - 2 * mm,
        "sub_rx": right - 2 * mm,
    }


def _pdf_tbl_hdr(pdf, y, layout):
    left, tw = layout["left"], layout["tw"]
    _rrect(pdf, left, y - 7 * mm, tw, 7.5 * mm, r=1.5 * mm, fill=BRAND_TEAL)
    pdf.setFont("Helvetica-Bold", 8)
    pdf.setFillColor(BRAND_WHITE)
    row_y = y - 5 * mm
    pdf.drawString(layout["name_x"], row_y, "Product")
    pdf.drawCentredString(layout["qty_cx"], row_y, "Qty")
    pdf.drawRightString(layout["unit_rx"], row_y, "Unit Price")
    pdf.drawRightString(layout["sub_rx"], row_y, "Subtotal")
    return y - 9 * mm


def _pdf_tbl_row(pdf, y, layout, product_name, qty, unit_price, line_sub, row_n):
    left, tw = layout["left"], layout["tw"]
    row_y = y - 3.8 * mm
    pdf.setFillColor(BRAND_ROW_ALT if row_n % 2 == 0 else BRAND_WHITE)
    pdf.rect(left, y - 5.5 * mm, tw, 5.5 * mm, fill=1, stroke=0)
    name_max = int((layout["name_end"] - layout["name_x"]) / (2.2 * mm) * 2.5)
    pdf.setFont("Helvetica-Bold", 7.5)
    pdf.setFillColor(BRAND_TEXT)
    pdf.drawString(layout["name_x"], row_y, str(product_name)[: max(name_max, 20)])
    pdf.setFont("Helvetica", 7.5)
    pdf.drawCentredString(layout["qty_cx"], row_y, str(qty))
    pdf.drawRightString(layout["unit_rx"], row_y, f"AED {unit_price:.2f}")
    pdf.drawRightString(layout["sub_rx"], row_y, f"AED {line_sub:.2f}")
    pdf.setStrokeColor(HexColor("#D0E8EF"))
    pdf.setLineWidth(0.3)
    pdf.line(left, y - 5.5 * mm, layout["right"], y - 5.5 * mm)
    return y - 6 * mm


def _pdf_meta_card(pdf, x, y, w, h, label, value):
    _rrect(pdf, x, y - h, w, h, r=2 * mm, stroke=HexColor("#B8D4DE"), lw=0.6)
    pdf.setFillColor(BRAND_WHITE)
    pdf.rect(x + 0.5 * mm, y - h + 0.5 * mm, w - 1 * mm, h - 1 * mm, fill=1, stroke=0)
    pdf.setFont("Helvetica", 6.5)
    pdf.setFillColor(BRAND_MUTED)
    pdf.drawString(x + 3 * mm, y - 5 * mm, label.upper())
    pdf.setFont("Helvetica-Bold", 8.5)
    pdf.setFillColor(BRAND_NAVY)
    pdf.drawString(x + 3 * mm, y - 11 * mm, str(value)[:28])


def _pdf_badge(pdf, rx, y, status):
    """Draw status badge with its right edge at rx. Returns y below the badge."""
    label = _STATUS_MAP.get(status, status.upper())
    badge_w = (len(label) * 4.6 + 14) * mm
    badge_h = 7.5 * mm
    badge_bottom = y - 5.5 * mm
    bx = rx - badge_w
    _rrect(pdf, bx, badge_bottom, badge_w, badge_h, r=2 * mm, fill=BRAND_TEAL)
    pdf.setFont("Helvetica-Bold", 7.5)
    pdf.setFillColor(BRAND_WHITE)
    pdf.drawCentredString(bx + badge_w / 2, y - 1.8 * mm, label)
    return badge_bottom


def _pdf_draw_status_date_block(pdf, rx, badge_y, status, date_str):
    """PAID badge with date beneath it — both right-aligned to rx."""
    badge_bottom = _pdf_badge(pdf, rx, badge_y, status)
    date_y = badge_bottom - 4.5 * mm
    pdf.setFont("Helvetica", 8.5)
    pdf.setFillColor(BRAND_MUTED)
    pdf.drawRightString(rx, date_y, f"Date: {date_str}")
    return date_y


# ══════════════════════════════════════════════════════════════════════════════
#  1.  RECEIPT IMAGE  (PIL)
# ══════════════════════════════════════════════════════════════════════════════
def render_receipt_image(order, receipt, logo_path=None) -> BytesIO:
    """Returns a BytesIO PNG of a clean receipt card."""
    if logo_path is None:
        from django.conf import settings
        logo_path = os.path.join(settings.MEDIA_ROOT, 'logos', 'logo.png')

    items   = list(order.items.all())
    W       = 900
    PAD     = 40
    ROW_H   = 32
    HDR_H   = 180
    BODY_H  = (
        80
        + 60
        + 40 * len(items)
        + 80
    )
    H = HDR_H + BODY_H + PAD * 2

    img  = Image.new("RGB", (W, H), "#FAFAFA")
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, W, HDR_H], fill="#111111")
    draw.rectangle([0, 0, W, 8],             fill="#1DB8B8")
    draw.rectangle([0, HDR_H - 5, W, HDR_H], fill="#E8433A")

    logo_pil = _prepare_logo_pil(logo_path)
    if logo_pil:
        logo_target_h = HDR_H - 30
        ratio         = logo_pil.width / logo_pil.height
        logo_target_w = int(logo_target_h * ratio)
        logo_resized  = logo_pil.resize((logo_target_w, logo_target_h), Image.LANCZOS)
        img.paste(logo_resized, (PAD, 15), logo_resized)

    try:
        fn_bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
        fn_reg  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        fn_sm   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
        fn_body = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
        fn_hdr  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
    except:
        fn_bold = fn_reg = fn_sm = fn_body = fn_hdr = ImageFont.load_default()

    def rtext(draw, x, y, text, font, fill):
        bb = draw.textbbox((0, 0), text, font=font)
        draw.text((x - (bb[2] - bb[0]), y), text, font=font, fill=fill)

    co_top = 20
    rtext(draw, W - PAD, co_top,      "SIMAK FRESH LLC",             fn_bold, "#FFFFFF")
    rtext(draw, W - PAD, co_top + 28, "Sharjah Media City, Sharjah", fn_sm,   "#CCCCCC")
    rtext(draw, W - PAD, co_top + 46, "Mushif Mall, Abu Dhabi",      fn_sm,   "#CCCCCC")
    rtext(draw, W - PAD, co_top + 64, "www.simakfresh.ae",           fn_sm,   "#CCCCCC")

    y = HDR_H + PAD

    def hline(yy, col="#CCCCCC", thick=1):
        draw.rectangle([PAD, yy, W - PAD, yy + thick], fill=col)

    draw.text((PAD, y),        "RECEIPT",          font=fn_bold, fill="#111111")
    rtext(draw, W - PAD, y,   f"# {receipt.receipt_number}", fn_bold, "#111111")
    y += 30
    draw.text((PAD, y),        f"Order: {order.id}", font=fn_body, fill="#444444")
    rtext(draw, W - PAD, y,
          receipt.generated_at.strftime("%d %b %Y %H:%M"), fn_body, "#444444")
    y += 30
    hline(y); y += 15

    user  = order.user
    cname = f"{user.first_name or ''} {user.last_name or ''}".strip() or str(user)
    draw.text((PAD, y), "CUSTOMER",  font=fn_hdr,  fill="#111111"); y += 22
    draw.text((PAD, y), cname,       font=fn_body, fill="#111111"); y += 22
    if getattr(user, 'email', None):
        draw.text((PAD, y), user.email,        font=fn_sm, fill="#444444"); y += 20
    if getattr(user, 'phone_number', None):
        draw.text((PAD, y), user.phone_number, font=fn_sm, fill="#444444"); y += 20
    hline(y + 8); y += 25

    draw.rectangle([PAD, y, W - PAD, y + 28], fill="#111111")
    draw.text((PAD + 10, y + 7),        "Product",  font=fn_hdr, fill="white")
    rtext(draw, W - PAD - 10, y + 7,   "Subtotal", fn_hdr,      "white")
    draw.text((int(W * 0.55), y + 7),   "Qty",      font=fn_hdr, fill="white")
    draw.text((int(W * 0.65), y + 7),   "Unit",     font=fn_hdr, fill="white")
    y += 30

    subtotal = Decimal("0.00")
    for i, item in enumerate(items):
        bg = "#EEEEEE" if i % 2 == 0 else "#FAFAFA"
        draw.rectangle([PAD, y, W - PAD, y + ROW_H - 2], fill=bg)
        draw.text((PAD + 10,        y + 6), str(item.product_name)[:35], font=fn_body, fill="#111111")
        draw.text((int(W * 0.55),   y + 6), str(item.quantity),          font=fn_body, fill="#111111")
        draw.text((int(W * 0.65),   y + 6), f"AED {item.price}",         font=fn_body, fill="#111111")
        rtext(draw, W - PAD - 10,  y + 6,  f"AED {item.subtotal}",      fn_body, "#111111")
        subtotal += Decimal(str(item.subtotal))
        y += ROW_H

    hline(y + 5, "#111111", 2); y += 18

    discount = Decimal(str(getattr(order, 'discount_amount', 0) or 0))
    delivery = Decimal(str(getattr(order, 'delivery_charge', 0) or 0))
    tip      = Decimal(str(getattr(order, 'tip_amount',      0) or 0))
    total    = Decimal(str(order.total_amount))

    for label, amt in [
        ("Subtotal", f"AED {subtotal:.2f}"),
        *([("Discount", f"- AED {discount:.2f}")] if discount else []),
        *([("Delivery", f"AED {delivery:.2f}")]   if delivery else []),
        *([("Tip",      f"AED {tip:.2f}")]         if tip      else []),
    ]:
        draw.text((int(W * 0.65), y), label + ":", font=fn_body, fill="#444444")
        rtext(draw, W - PAD, y, amt, fn_body, "#111111"); y += 24

    hline(y + 2, "#111111"); y += 10
    draw.rectangle([int(W * 0.60), y, W - PAD, y + 36], fill="#111111")
    draw.text((int(W * 0.63), y + 9),    "TOTAL:",          font=fn_bold, fill="white")
    rtext(draw, W - PAD - 10, y + 9,    f"AED {total:.2f}", fn_bold, "white")
    y += 50

    hline(y, "#CCCCCC"); y += 12
    draw.text((PAD, y),
        f"Ref: {receipt.receipt_number}  |  Thank you for choosing Simak Fresh",
        font=fn_sm, fill="#888888")

    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf


# ══════════════════════════════════════════════════════════════════════════════
#  2.  STANDARD CUSTOMER PDF RECEIPT
# ══════════════════════════════════════════════════════════════════════════════
def render_receipt_pdf(order, receipt, logo_path=None) -> BytesIO:
    """Customer-facing PDF receipt — Simak Fresh website branding."""
    if logo_path is None:
        logo_path = _default_pdf_logo_path()

    logo_reader = _prepare_logo_pdf(logo_path)
    generated_at = receipt.generated_at.strftime("%d-%b-%Y %H:%M")

    payment = getattr(order, "payment", None)
    pay_method = _pdf_payment_method_label(payment)

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    pdf.setFillColor(BRAND_BODY_BG)
    pdf.rect(0, 0, width, height, fill=1, stroke=0)

    _draw_pdf_header(pdf, width, height, logo_reader)

    y = height - PDF_HEADER_H - 10 * mm
    rx = width - MR
    pdf.setFont("Helvetica-Bold", 16)
    pdf.setFillColor(BRAND_NAVY)
    pdf.drawString(ML, y, "PAYMENT RECEIPT")
    date_y = _pdf_draw_status_date_block(
        pdf, rx, y, order.get_status_display(), generated_at,
    )

    y = date_y - 6.5 * mm
    pdf.setFont("Helvetica", 8.5)
    pdf.setFillColor(BRAND_MUTED)
    pdf.drawString(ML, y, f"Receipt No: {receipt.receipt_number}")
    y -= 3 * mm
    pdf.setStrokeColor(HexColor("#B8D4DE"))
    pdf.setLineWidth(0.5)
    pdf.line(ML, y, width - MR, y)
    y -= 7 * mm

    col_w = (width - ML - MR - 5 * mm) / 2
    c1x, c2x = ML, ML + col_w + 5 * mm
    top = y

    y1 = _pdf_section(pdf, c1x, top, "Customer", sw=col_w)
    user = order.user
    cname = f"{user.first_name or ''} {user.last_name or ''}".strip() or str(user)
    y1 = _pdf_kv(pdf, c1x, y1, "Name:", cname, val_max_chars=36)
    if getattr(user, "email", None):
        y1 = _pdf_kv(pdf, c1x, y1, "Email:", user.email, val_max_chars=36)
    if getattr(user, "phone_number", None):
        y1 = _pdf_kv(pdf, c1x, y1, "Phone:", user.phone_number)

    y2 = _pdf_section(pdf, c2x, top, "Order Details", sw=col_w)
    y2 = _pdf_kv(pdf, c2x, y2, "Order ID:", f"#{order.id}")
    y2 = _pdf_kv(pdf, c2x, y2, "Order Date:", order.created_at.strftime("%d %b %Y"))
    y2 = _pdf_kv(pdf, c2x, y2, "Payment:", "PAID")
    y2 = _pdf_kv(pdf, c2x, y2, "Method:", pay_method)

    y = min(y1, y2) - 5 * mm

    if getattr(order, "shipping_address", None):
        addr = order.shipping_address
        y = _pdf_section(pdf, ML, y, "Delivery Address", sw=width - ML - MR)
        pdf.setFont("Helvetica", 8)
        pdf.setFillColor(BRAND_TEXT)
        lines = []
        if getattr(addr, "full_name", None):
            lines.append(addr.full_name)
        bld = " ".join(
            filter(
                None,
                [getattr(addr, "building_name", ""), getattr(addr, "flat_villa_number", "")],
            )
        ).strip()
        if bld:
            lines.append(bld)
        if getattr(addr, "street_address", None):
            lines.append(addr.street_address)
        if getattr(addr, "area", None):
            lines.append(addr.area)
        emirate = (
            addr.get_emirate_display()
            if hasattr(addr, "get_emirate_display")
            else getattr(addr, "emirate", "")
        )
        city = getattr(addr, "city", "")
        if city or emirate:
            lines.append(", ".join(filter(None, [city, emirate])))
        for ln in lines[:5]:
            if ln:
                pdf.drawString(ML, y, str(ln)[:58])
                y -= 3.8 * mm
        y -= 4 * mm

    y = _pdf_section(pdf, ML, y, "Order Items", sw=width - ML - MR)
    y -= 1 * mm
    table_right = width - MR
    layout = _pdf_table_layout(ML, table_right)
    pg = 1
    y = _pdf_tbl_hdr(pdf, y, layout)

    subtotal = Decimal("0.00")
    row_n = 0
    for item in order.items.all():
        if y < FOOTER_H + 52 * mm:
            _draw_pdf_footer(pdf, width, pg, "?", receipt.receipt_number, generated_at)
            pdf.showPage()
            pg += 1
            pdf.setFillColor(BRAND_BODY_BG)
            pdf.rect(0, 0, width, height, fill=1, stroke=0)
            _draw_pdf_header(pdf, width, height, logo_reader, compact=True)
            y = height - PDF_HEADER_H - 12 * mm
            y = _pdf_tbl_hdr(pdf, y, layout)
            row_n = 0

        unit_price = Decimal(str(item.price))
        line_sub = Decimal(str(item.subtotal))
        subtotal += line_sub
        y = _pdf_tbl_row(
            pdf, y, layout, item.product_name, item.quantity,
            unit_price, line_sub, row_n,
        )
        row_n += 1

    y -= 3 * mm
    pdf.setStrokeColor(HexColor("#B8D4DE"))
    pdf.setLineWidth(0.5)
    pdf.line(ML, y, width - MR, y)
    y -= 4 * mm

    min_y_totals = PDF_THANK_Y + 22 * mm
    if y < min_y_totals:
        _draw_pdf_footer(pdf, width, pg, "?", receipt.receipt_number, generated_at)
        pdf.showPage()
        pg += 1
        pdf.setFillColor(BRAND_BODY_BG)
        pdf.rect(0, 0, width, height, fill=1, stroke=0)
        _draw_pdf_header(pdf, width, height, logo_reader, compact=True)
        y = height - PDF_HEADER_H - 14 * mm

    srx = width - MR
    discount = Decimal(str(getattr(order, "discount_amount", 0) or 0))
    delivery = Decimal(str(getattr(order, "delivery_charge", 0) or 0))
    tip = Decimal(str(getattr(order, "tip_amount", 0) or 0))
    total = Decimal(str(order.total_amount))

    def srow(lbl, amt, prefix=""):
        nonlocal y
        pdf.setFont("Helvetica", 9)
        pdf.setFillColor(BRAND_MUTED)
        pdf.drawRightString(srx - 34 * mm, y, lbl)
        pdf.setFillColor(BRAND_TEXT)
        pdf.drawRightString(srx, y, f"{prefix}{amt}")
        y -= 5 * mm

    srow("Subtotal:", f"AED {subtotal:.2f}")
    if discount > 0:
        srow("Discount:", f"AED {discount:.2f}", "- ")
    if delivery > 0:
        srow("Delivery:", f"AED {delivery:.2f}")
    if tip > 0:
        srow("Tip:", f"AED {tip:.2f}")

    y -= 1 * mm
    sx = ML + 88 * mm
    _rrect(pdf, sx, y - 11 * mm + 2 * mm, srx - sx, 12 * mm, r=2.5 * mm, fill=BRAND_NAVY)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.setFillColor(BRAND_WHITE)
    pdf.drawRightString(srx - 34 * mm, y - 6.5 * mm, "TOTAL PAID:")
    pdf.drawRightString(srx - 2 * mm, y - 6.5 * mm, f"AED {total:.2f}")

    _draw_pdf_thank_you(pdf, width)
    _draw_pdf_footer(pdf, width, pg, pg, receipt.receipt_number, generated_at)
    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer


# ══════════════════════════════════════════════════════════════════════════════
#  3.  ADMIN PDF RECEIPT  (full-featured)
# ══════════════════════════════════════════════════════════════════════════════
def render_admin_receipt_pdf(order, logo_path=None) -> BytesIO:
    """Full admin receipt — branded layout, QR code, delivery details."""
    if logo_path is None:
        logo_path = _default_pdf_logo_path()

    logo_reader = _prepare_logo_pdf(logo_path)
    payment = getattr(order, "payment", None)
    pay_method = _pdf_payment_method_label(payment)
    pay_status = payment.get_status_display() if payment else "—"
    receipt = getattr(payment, "receipt", None) if payment else None
    ref = receipt.receipt_number if receipt else f"ORD-{order.id}"

    qr_reader = _make_qr(
        f"SIMAK:{order.id}|AED {order.total_amount}|"
        f"{order.created_at.strftime('%Y-%m-%d')}"
    )

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    generated_at = datetime.now().strftime("%d-%b-%Y %H:%M")
    table_right = width - MR

    pdf.setFillColor(BRAND_BODY_BG)
    pdf.rect(0, 0, width, height, fill=1, stroke=0)

    _draw_pdf_header(pdf, width, height, logo_reader)

    title_y = height - PDF_HEADER_H - 10 * mm
    pdf.setFont("Helvetica-Bold", 16)
    pdf.setFillColor(BRAND_NAVY)
    pdf.drawString(ML, title_y, "ORDER RECEIPT")
    _pdf_badge(pdf, width - MR, title_y, order.get_status_display())

    meta_y = title_y - 8 * mm
    cw, ch, cg = 41 * mm, 16 * mm, 3.5 * mm
    cx = ML
    for label, val in [
        ("Order ID", f"#{order.id}"),
        ("Order Date", order.created_at.strftime("%d %b %Y")),
        ("Time", order.created_at.strftime("%I:%M %p")),
        ("Payment", pay_method),
    ]:
        _pdf_meta_card(pdf, cx, meta_y, cw, ch, label, val)
        cx += cw + cg

    y = meta_y - ch - 7 * mm

    col_w = (width - ML - MR - 5 * mm) / 2
    c1x, c2x = ML, ML + col_w + 5 * mm
    top = y

    y1 = _pdf_section(pdf, c1x, top, "Customer", sw=col_w)
    user = order.user
    cname = f"{user.first_name or ''} {user.last_name or ''}".strip() or str(user)
    y1 = _pdf_kv(pdf, c1x, y1, "Name:", cname, val_max_chars=34)
    if getattr(user, "email", None):
        y1 = _pdf_kv(pdf, c1x, y1, "Email:", user.email, val_max_chars=34)
    if getattr(user, "phone_number", None):
        y1 = _pdf_kv(pdf, c1x, y1, "Phone:", user.phone_number)

    y2 = _pdf_section(pdf, c2x, top, "Delivery Info", sw=col_w)
    if getattr(order, "preferred_delivery_date", None):
        y2 = _pdf_kv(pdf, c2x, y2, "Date:", order.preferred_delivery_date)
    if getattr(order, "preferred_delivery_slot", None):
        y2 = _pdf_kv(pdf, c2x, y2, "Slot:", str(order.preferred_delivery_slot)[:28])
    y2 = _pdf_kv(pdf, c2x, y2, "Payment:", pay_status)

    y = min(y1, y2) - 5 * mm

    if getattr(order, "shipping_address", None):
        addr = order.shipping_address
        y = _pdf_section(pdf, ML, y, "Delivery Address", sw=width - ML - MR)
        pdf.setFont("Helvetica", 8)
        pdf.setFillColor(BRAND_TEXT)
        parts = []
        if getattr(addr, "full_name", None):
            parts.append(addr.full_name)
        if getattr(addr, "phone_number", None):
            parts.append(f"Ph: {addr.phone_number}")
        bld = " ".join(
            filter(
                None,
                [getattr(addr, "building_name", ""), getattr(addr, "flat_villa_number", "")],
            )
        ).strip()
        if bld:
            parts.append(bld)
        if getattr(addr, "street_address", None):
            parts.append(addr.street_address)
        if getattr(addr, "area", None):
            parts.append(addr.area)
        emirate = (
            addr.get_emirate_display()
            if hasattr(addr, "get_emirate_display")
            else getattr(addr, "emirate", "")
        )
        city = getattr(addr, "city", "")
        if city or emirate:
            parts.append(", ".join(filter(None, [city, emirate])))
        for ln in parts[:6]:
            pdf.drawString(ML, y, str(ln)[:58])
            y -= 3.8 * mm
        y -= 4 * mm

    if getattr(order, "delivery_notes", None):
        y = _pdf_section(pdf, ML, y, "Delivery Notes", sw=width - ML - MR)
        pdf.setFont("Helvetica-Oblique", 8)
        pdf.setFillColor(BRAND_MUTED)
        pdf.drawString(ML, y, str(order.delivery_notes)[:90])
        y -= 5 * mm

    y = _pdf_section(pdf, ML, y, "Order Items", sw=width - ML - MR)
    y -= 1 * mm
    layout = _pdf_table_layout(ML, table_right)
    pg = 1
    row_n = 0
    y = _pdf_tbl_hdr(pdf, y, layout)
    subtotal = Decimal("0.00")

    for item in order.items.all():
        if y < FOOTER_H + 58 * mm:
            _draw_pdf_footer(pdf, width, pg, "?", ref, generated_at)
            pdf.showPage()
            pg += 1
            pdf.setFillColor(BRAND_BODY_BG)
            pdf.rect(0, 0, width, height, fill=1, stroke=0)
            _draw_pdf_header(pdf, width, height, logo_reader, compact=True)
            y = height - PDF_HEADER_H - 12 * mm
            pdf.setFont("Helvetica-Bold", 11)
            pdf.setFillColor(BRAND_NAVY)
            pdf.drawString(ML, y, "ORDER ITEMS (continued)")
            y -= 7 * mm
            y = _pdf_tbl_hdr(pdf, y, layout)
            row_n = 0

        unit_price = Decimal(str(item.price))
        line_sub = Decimal(str(item.subtotal))
        subtotal += line_sub
        y = _pdf_tbl_row(
            pdf, y, layout, item.product_name, item.quantity,
            unit_price, line_sub, row_n,
        )
        row_n += 1

    y -= 3 * mm
    pdf.setStrokeColor(HexColor("#B8D4DE"))
    pdf.setLineWidth(0.5)
    pdf.line(ML, y, table_right, y)
    y -= 6 * mm

    qr_sz = 28 * mm
    sum_x = ML + qr_sz + 12 * mm
    srx = table_right

    discount = Decimal(str(getattr(order, "discount_amount", 0) or 0))
    delivery = Decimal(str(getattr(order, "delivery_charge", 0) or 0))
    tip = Decimal(str(getattr(order, "tip_amount", 0) or 0))
    total = Decimal(str(order.total_amount))

    sy_start = y

    def _sr(lbl, amt, prefix=""):
        nonlocal y
        pdf.setFont("Helvetica", 9)
        pdf.setFillColor(BRAND_MUTED)
        pdf.drawRightString(srx - 34 * mm, y, lbl)
        pdf.setFillColor(BRAND_TEXT)
        pdf.drawRightString(srx, y, f"{prefix}{amt}")
        y -= 5 * mm

    _sr("Subtotal:", f"AED {subtotal:.2f}")
    if discount > 0:
        _sr("Discount:", f"AED {discount:.2f}", "- ")
    if delivery > 0:
        _sr("Delivery:", f"AED {delivery:.2f}")
    if tip > 0:
        _sr("Tip:", f"AED {tip:.2f}")

    y -= 1 * mm
    _rrect(pdf, sum_x, y - 11 * mm + 2 * mm, srx - sum_x, 12 * mm, r=2.5 * mm, fill=BRAND_NAVY)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.setFillColor(BRAND_WHITE)
    pdf.drawRightString(srx - 34 * mm, y - 6.5 * mm, "TOTAL:")
    pdf.drawRightString(srx - 2 * mm, y - 6.5 * mm, f"AED {total:.2f}")
    y -= 12 * mm

    sy_end = y
    qr_y = sy_start - ((sy_start - sy_end - qr_sz) / 2) - qr_sz
    pdf.drawImage(qr_reader, ML, qr_y, width=qr_sz, height=qr_sz)
    pdf.setFont("Helvetica", 6.5)
    pdf.setFillColor(BRAND_MUTED)
    pdf.drawCentredString(ML + qr_sz / 2, qr_y - 3.5 * mm, "Scan to verify order")

    pay_y = min(qr_y - 7 * mm, sy_end - 1 * mm)
    pdf.setFont("Helvetica-Bold", 8.5)
    pdf.setFillColor(BRAND_NAVY)
    pdf.drawString(
        ML, pay_y,
        f"Payment: {pay_method}   |   Status: {pay_status}",
    )

    _draw_pdf_footer(pdf, width, pg, pg, ref, generated_at)
    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer


