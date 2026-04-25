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
FOOTER_H = 14 * mm


# ══════════════════════════════════════════════════════════════════════════════
#  LOGO HELPERS
# ══════════════════════════════════════════════════════════════════════════════
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
        "www.simakfresh.ae  |  +971 XX XXX XXXX",
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
    """Clean customer-facing PDF receipt."""
    if logo_path is None:
        from django.conf import settings
        logo_path = os.path.join(settings.MEDIA_ROOT, 'logos', 'logo.png')

    logo_reader  = _prepare_logo(logo_path)
    generated_at = datetime.now().strftime("%d-%b-%Y %H:%M")

    buffer = BytesIO()
    pdf    = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    _draw_header(pdf, width, height, logo_reader)

    y = height - HEADER_H - 9*mm
    pdf.setFont("Helvetica-Bold", 14)
    pdf.setFillColor(PRIMARY)
    pdf.drawString(ML, y, "RECEIPT")
    _badge(pdf, width - MR, y, order.get_status_display())

    y -= 7*mm
    pdf.setFont("Helvetica", 8); pdf.setFillColor(MUTED)
    pdf.drawString(ML, y, f"Receipt No: {receipt.receipt_number}")
    pdf.drawRightString(width - MR, y,
        f"Date: {receipt.generated_at.strftime('%d-%b-%Y %H:%M')}")
    y -= 3*mm
    pdf.setStrokeColor(RULE_STR); pdf.setLineWidth(0.4)
    pdf.line(ML, y, width - MR, y); y -= 7*mm

    col_w = (width - ML - MR - 5*mm) / 2
    c1x, c2x = ML, ML + col_w + 5*mm
    top = y

    y1 = _section(pdf, c1x, top, "Customer", sw=col_w)
    user  = order.user
    cname = f"{user.first_name or ''} {user.last_name or ''}".strip() or str(user)
    y1 = _kv(pdf, c1x, y1, "Name:",  cname)
    if getattr(user, 'email', None):
        y1 = _kv(pdf, c1x, y1, "Email:", user.email[:28])
    if getattr(user, 'phone_number', None):
        y1 = _kv(pdf, c1x, y1, "Phone:", user.phone_number)

    y2 = _section(pdf, c2x, top, "Order Details", sw=col_w)
    y2 = _kv(pdf, c2x, y2, "Order ID:", f"#{order.id}")
    y2 = _kv(pdf, c2x, y2, "Order Date:", order.created_at.strftime("%d %b %Y"))
    pay_status = getattr(order, 'payment_status', 'Paid')
    marker = "[PAID]" if pay_status == "Paid" else f"[{pay_status.upper()}]"
    y2 = _kv(pdf, c2x, y2, "Payment:", marker)
    y2 = _kv(pdf, c2x, y2, "Method:", getattr(order, 'payment_method', 'Card'))

    y = min(y1, y2) - 5*mm

    if getattr(order, 'shipping_address', None):
        addr = order.shipping_address
        y    = _section(pdf, ML, y, "Shipping Address")
        pdf.setFont("Helvetica", 7.5); pdf.setFillColor(TEXT)
        lines = []
        if getattr(addr, 'full_name', None): lines.append(addr.full_name)
        bld = " ".join(filter(None, [
            getattr(addr, 'building_name', ''),
            getattr(addr, 'flat_villa_number', '')])).strip()
        if bld: lines.append(bld)
        if getattr(addr, 'street_address', None): lines.append(addr.street_address)
        if getattr(addr, 'area', None): lines.append(addr.area)
        emirate = (addr.get_emirate_display()
                   if hasattr(addr, 'get_emirate_display')
                   else getattr(addr, 'emirate', ''))
        city = getattr(addr, 'city', '')
        if city or emirate:
            lines.append(", ".join(filter(None, [city, emirate])))
        for ln in lines[:5]:
            if ln:
                pdf.drawString(ML, y, str(ln)[:55]); y -= 3.8*mm
        y -= 4*mm

    y    = _section(pdf, ML, y, "Items", sw=width - ML - MR)
    y   -= 1*mm
    TW   = width - ML - MR
    COL  = {'name': ML, 'qty': ML+95*mm, 'price': ML+115*mm, 'sub': width-MR}
    pg   = 1
    y    = _tbl_hdr(pdf, y, TW, COL, width)

    subtotal = Decimal("0.00")
    row_n    = 0
    for item in order.items.all():
        if y < FOOTER_H + 45*mm:
            _draw_footer(pdf, width, pg, "?", receipt.receipt_number, generated_at)
            pdf.showPage(); pg += 1
            _draw_header(pdf, width, height, logo_reader, compact=True)
            y = height - HEADER_H - 10*mm
            y = _tbl_hdr(pdf, y, TW, COL, width); row_n = 0

        pdf.setFillColor(ROW_ALT if row_n % 2 == 0 else WHITE_COL)
        pdf.rect(ML, y - 5.5*mm, TW, 5.5*mm, fill=1, stroke=0)
        pdf.setFont("Helvetica-Bold", 7.5); pdf.setFillColor(TEXT)
        pdf.drawString(COL['name']+2*mm, y-3.8*mm, str(item.product_name)[:40])
        pdf.setFont("Helvetica", 7.5)
        up = Decimal(str(item.price)); sub = Decimal(str(item.subtotal))
        subtotal += sub
        pdf.drawCentredString(COL['qty']+10*mm, y-3.8*mm, str(item.quantity))
        pdf.drawString(COL['price'],             y-3.8*mm, f"AED {up:.2f}")
        pdf.drawRightString(COL['sub']-1*mm,     y-3.8*mm, f"AED {sub:.2f}")
        pdf.setStrokeColor(HexColor("#CCCCCC")); pdf.setLineWidth(0.3)
        pdf.line(ML, y-5.5*mm, width-MR, y-5.5*mm)
        y -= 6*mm; row_n += 1

    y -= 3*mm
    pdf.setStrokeColor(RULE_STR); pdf.setLineWidth(0.5)
    pdf.line(ML, y, width-MR, y); y -= 4*mm

    SRX = width - MR
    discount = Decimal(str(getattr(order, 'discount_amount', 0) or 0))
    delivery = Decimal(str(getattr(order, 'delivery_charge', 0) or 0))
    tip      = Decimal(str(getattr(order, 'tip_amount',      0) or 0))
    total    = Decimal(str(order.total_amount))

    def srow(lbl, amt, prefix=""):
        nonlocal y
        pdf.setFont("Helvetica", 8.5); pdf.setFillColor(TEXT)
        pdf.drawRightString(SRX-32*mm, y, lbl)
        pdf.drawRightString(SRX, y, f"{prefix}{amt}"); y -= 5*mm

    srow("Subtotal:", f"AED {subtotal:.2f}")
    if discount > 0: srow("Discount:", f"AED {discount:.2f}", "- ")
    if delivery > 0: srow("Delivery:", f"AED {delivery:.2f}")
    if tip      > 0: srow("Tip:",      f"AED {tip:.2f}")

    y -= 1*mm
    SX = ML + 90*mm
    pdf.setStrokeColor(PRIMARY); pdf.setLineWidth(0.5)
    pdf.line(SX, y, SRX, y); y -= 1.2*mm
    pdf.line(SX, y, SRX, y); y -= 5*mm

    _rrect(pdf, SX, y-10*mm+2*mm, SRX-SX, 11*mm, r=2*mm, fill=PRIMARY)
    pdf.setFont("Helvetica-Bold", 11); pdf.setFillColor(WHITE_COL)
    pdf.drawRightString(SRX-33*mm, y-6*mm, "TOTAL:")
    pdf.drawRightString(SRX-1*mm,  y-6*mm, f"AED {total:.2f}")

    _draw_footer(pdf, width, pg, pg, receipt.receipt_number, generated_at)
    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer


# ══════════════════════════════════════════════════════════════════════════════
#  3.  ADMIN PDF RECEIPT  (full-featured)
# ══════════════════════════════════════════════════════════════════════════════
def render_admin_receipt_pdf(order, logo_path=None) -> BytesIO:
    """Full admin receipt — QR code, delivery details, address, meta cards."""
    if logo_path is None:
        from django.conf import settings
        logo_path = os.path.join(settings.MEDIA_ROOT, 'logos', 'logo.png')

    logo_reader  = _prepare_logo(logo_path)
    qr_reader    = _make_qr(
        f"SIMAK:{order.id}|AED {order.total_amount}|"
        f"{order.created_at.strftime('%Y-%m-%d')}")

    buffer = BytesIO()
    pdf    = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    generated_at  = datetime.now().strftime("%d-%b-%Y %H:%M")

    _draw_header(pdf, width, height, logo_reader)

    title_y = height - HEADER_H - 9*mm
    pdf.setFont("Helvetica-Bold", 15); pdf.setFillColor(PRIMARY)
    pdf.drawString(ML, title_y, "ORDER RECEIPT")
    _badge(pdf, width - MR, title_y, order.get_status_display())

    meta_y = title_y - 7*mm
    cw, ch, cg = 42*mm, 16*mm, 3*mm
    cx = ML
    for label, val in [
        ("Order ID",   f"#{order.id}"),
        ("Order Date", order.created_at.strftime("%d %b %Y")),
        ("Time",       order.created_at.strftime("%I:%M %p")),
        ("Payment",    getattr(order, 'payment_method', 'Card')),
    ]:
        _rrect(pdf, cx, meta_y - ch, cw, ch, r=2*mm, stroke=RULE_STR, lw=0.5)
        pdf.setFont("Helvetica", 6.5); pdf.setFillColor(MUTED)
        pdf.drawString(cx + 3*mm, meta_y - 5*mm, label)
        pdf.setFont("Helvetica-Bold", 8.5); pdf.setFillColor(TEXT)
        pdf.drawString(cx + 3*mm, meta_y - 11*mm, str(val))
        cx += cw + cg

    y = meta_y - ch - 7*mm

    col_w = (width - ML - MR - 5*mm) / 2
    c1x, c2x = ML, ML + col_w + 5*mm
    top = y

    y1 = _section(pdf, c1x, top, "Customer", sw=col_w)
    user  = order.user
    cname = f"{user.first_name or ''} {user.last_name or ''}".strip() or str(user)
    y1 = _kv(pdf, c1x, y1, "Name:",  cname)
    if getattr(user, 'email', None):
        y1 = _kv(pdf, c1x, y1, "Email:", user.email[:28])
    if getattr(user, 'phone_number', None):
        y1 = _kv(pdf, c1x, y1, "Phone:", user.phone_number)

    y2 = _section(pdf, c2x, top, "Delivery Info", sw=col_w)
    if getattr(order, 'preferred_delivery_date', None):
        y2 = _kv(pdf, c2x, y2, "Date:", str(order.preferred_delivery_date))
    if getattr(order, 'preferred_delivery_slot', None):
        y2 = _kv(pdf, c2x, y2, "Slot:", str(order.preferred_delivery_slot)[:25])
    pay_status = getattr(order, 'payment_status', 'Paid')
    marker     = "[PAID]" if pay_status == "Paid" else f"[{pay_status.upper()}]"
    y2 = _kv(pdf, c2x, y2, "Status:", marker)

    y = min(y1, y2) - 5*mm

    if getattr(order, 'shipping_address', None):
        addr  = order.shipping_address
        y     = _section(pdf, ML, y, "Shipping Address")
        parts = []
        if getattr(addr, 'full_name',         None): parts.append(addr.full_name)
        if getattr(addr, 'phone_number',       None): parts.append(f"Ph: {addr.phone_number}")
        bld = " ".join(filter(None, [
            getattr(addr, 'building_name', ''),
            getattr(addr, 'flat_villa_number', '')])).strip()
        if bld: parts.append(bld)
        if getattr(addr, 'street_address',     None): parts.append(addr.street_address)
        if getattr(addr, 'area',               None): parts.append(addr.area)
        emirate = (addr.get_emirate_display()
                   if hasattr(addr, 'get_emirate_display')
                   else getattr(addr, 'emirate', ''))
        city = getattr(addr, 'city', '')
        if city or emirate:
            parts.append(", ".join(filter(None, [city, emirate])))
        half = max(1, (len(parts) + 1) // 2)
        pdf.setFont("Helvetica", 7.5); pdf.setFillColor(TEXT)
        for i, ln in enumerate(parts[:6]):
            col_x = ML if i < half else ML + 90*mm
            row_y = y - (i % half) * 3.8*mm
            pdf.drawString(col_x, row_y, str(ln)[:42])
        y -= half * 3.8*mm + 5*mm

    if getattr(order, 'notes', None):
        y = _section(pdf, ML, y, "Order Notes")
        pdf.setFont("Helvetica-Oblique", 7.5); pdf.setFillColor(MUTED)
        pdf.drawString(ML, y, str(order.notes)[:90]); y -= 5*mm

    y   = _section(pdf, ML, y, "Order Items", sw=width - ML - MR)
    y  -= 1*mm
    TW  = width - ML - MR
    COL = {'name': ML, 'qty': ML+95*mm, 'price': ML+115*mm, 'sub': width-MR}
    pg  = 1; row_n = 0
    y   = _tbl_hdr(pdf, y, TW, COL, width)
    subtotal = Decimal("0.00")

    for item in order.items.all():
        if y < FOOTER_H + 55*mm:
            _draw_footer(pdf, width, pg, "?", order.id, generated_at)
            pdf.showPage(); pg += 1
            _draw_header(pdf, width, height, logo_reader, compact=True)
            y = height - HEADER_H - 10*mm
            pdf.setFont("Helvetica-Bold", 10); pdf.setFillColor(PRIMARY)
            pdf.drawString(ML, y, "ORDER ITEMS (Continued)"); y -= 6*mm
            y = _tbl_hdr(pdf, y, TW, COL, width); row_n = 0

        pdf.setFillColor(ROW_ALT if row_n % 2 == 0 else WHITE_COL)
        pdf.rect(ML, y - 5.5*mm, TW, 5.5*mm, fill=1, stroke=0)
        pdf.setFont("Helvetica-Bold", 7.5); pdf.setFillColor(TEXT)
        pdf.drawString(COL['name']+2*mm, y-3.8*mm, str(item.product_name)[:40])
        pdf.setFont("Helvetica", 7.5)
        up  = Decimal(str(item.price))
        sub = Decimal(str(item.subtotal))
        subtotal += sub
        pdf.drawCentredString(COL['qty']+10*mm, y-3.8*mm, str(item.quantity))
        pdf.drawString(COL['price'],             y-3.8*mm, f"AED {up:.2f}")
        pdf.drawRightString(COL['sub']-1*mm,     y-3.8*mm, f"AED {sub:.2f}")
        pdf.setStrokeColor(HexColor("#CCCCCC")); pdf.setLineWidth(0.3)
        pdf.line(ML, y-5.5*mm, width-MR, y-5.5*mm)
        y -= 6*mm; row_n += 1

    y -= 3*mm
    pdf.setStrokeColor(RULE_STR); pdf.setLineWidth(0.6)
    pdf.line(ML, y, width-MR, y); y -= 6*mm

    QR_SZ = 28*mm
    SUM_X = ML + QR_SZ + 14*mm
    SRX   = width - MR

    discount = Decimal(str(getattr(order, 'discount_amount', 0) or 0))
    delivery = Decimal(str(getattr(order, 'delivery_charge', 0) or 0))
    tip      = Decimal(str(getattr(order, 'tip_amount',      0) or 0))
    total    = Decimal(str(order.total_amount))

    sy_start = y

    def _sr(lbl, amt, prefix=""):
        nonlocal y
        pdf.setFont("Helvetica", 8.5); pdf.setFillColor(TEXT)
        pdf.drawRightString(SRX-32*mm, y, lbl)
        pdf.drawRightString(SRX, y, f"{prefix}{amt}"); y -= 5*mm

    _sr("Subtotal:", f"AED {subtotal:.2f}")
    if discount > 0: _sr("Discount:", f"AED {discount:.2f}", "- ")
    if delivery > 0: _sr("Delivery:", f"AED {delivery:.2f}")
    if tip      > 0: _sr("Tip:",      f"AED {tip:.2f}")

    y -= 1*mm
    pdf.setStrokeColor(PRIMARY); pdf.setLineWidth(0.5)
    pdf.line(SUM_X, y, SRX, y); y -= 1.2*mm
    pdf.line(SUM_X, y, SRX, y); y -= 5*mm

    _rrect(pdf, SUM_X, y-10*mm+2*mm, SRX-SUM_X, 11*mm, r=2*mm, fill=PRIMARY)
    pdf.setFont("Helvetica-Bold", 11); pdf.setFillColor(WHITE_COL)
    pdf.drawRightString(SRX-33*mm, y-6*mm, "TOTAL:")
    pdf.drawRightString(SRX-1*mm,  y-6*mm, f"AED {total:.2f}")
    y -= 11*mm

    sy_end = y
    qr_y   = sy_start - ((sy_start - sy_end - QR_SZ) / 2) - QR_SZ
    pdf.drawImage(qr_reader, ML, qr_y, width=QR_SZ, height=QR_SZ)
    pdf.setFont("Helvetica", 6); pdf.setFillColor(MUTED)
    pdf.drawCentredString(ML + QR_SZ/2, qr_y - 3.5*mm, "Scan to verify order")

    pay_y = min(qr_y - 6.5*mm, sy_end - 1*mm)
    pdf.setFont("Helvetica-Bold", 8); pdf.setFillColor(TEXT)
    pdf.drawString(ML, pay_y,
        f"Payment: {getattr(order, 'payment_method', 'Card')}   Status: {marker}")

    _draw_footer(pdf, width, pg, pg, order.id, generated_at)
    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer


