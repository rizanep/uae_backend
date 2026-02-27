from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm


def render_receipt_image(order, receipt):
    items = list(order.items.all())
    height = 300 + 30 * len(items)
    width = 800

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    y = 20
    draw.text((20, y), "Receipt", font=font, fill="black")
    y += 30
    draw.text((20, y), f"Receipt No: {receipt.receipt_number}", font=font, fill="black")
    y += 20
    draw.text((20, y), f"Order ID: {order.id}", font=font, fill="black")
    y += 20
    draw.text((20, y), f"Date: {receipt.generated_at.strftime('%Y-%m-%d %H:%M')}", font=font, fill="black")
    y += 20

    user = order.user
    customer_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or str(user)
    draw.text((20, y), f"Customer: {customer_name}", font=font, fill="black")
    y += 20
    if user.email:
        draw.text((20, y), f"Email: {user.email}", font=font, fill="black")
        y += 20

    draw.text((20, y), f"Total: {order.total_amount}", font=font, fill="black")
    y += 30

    draw.text((20, y), "Items:", font=font, fill="black")
    y += 20

    for item in items:
        line = f"- {item.product_name} x{item.quantity} @ {item.price} = {item.subtotal}"
        draw.text((20, y), line, font=font, fill="black")
        y += 20

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def render_receipt_pdf(order, receipt):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 30 * mm
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(20 * mm, y, "Receipt")
    y -= 10 * mm

    pdf.setFont("Helvetica", 10)
    pdf.drawString(20 * mm, y, f"Receipt No: {receipt.receipt_number}")
    y -= 6 * mm
    pdf.drawString(20 * mm, y, f"Order ID: {order.id}")
    y -= 6 * mm
    pdf.drawString(20 * mm, y, f"Date: {receipt.generated_at.strftime('%Y-%m-%d %H:%M')}")
    y -= 8 * mm

    user = order.user
    customer_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or str(user)
    pdf.drawString(20 * mm, y, f"Customer: {customer_name}")
    y -= 6 * mm
    if user.email:
        pdf.drawString(20 * mm, y, f"Email: {user.email}")
        y -= 6 * mm
    if user.phone_number:
        pdf.drawString(20 * mm, y, f"Phone: {user.phone_number}")
        y -= 8 * mm

    address = order.shipping_address
    if address:
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(20 * mm, y, "Shipping Address")
        y -= 6 * mm
        pdf.setFont("Helvetica", 9)
        lines = [
            address.full_name,
            address.street_address,
            address.area or "",
            f"{address.city}, {address.emirate.upper()}",
            (address.postal_code or "").strip(),
            "United Arab Emirates" if address.country == "AE" else address.country,
        ]
        for line in lines:
            if line:
                pdf.drawString(20 * mm, y, line)
                y -= 5 * mm
        y -= 5 * mm

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(20 * mm, y, "Items")
    y -= 6 * mm

    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(20 * mm, y, "Product")
    pdf.drawString(100 * mm, y, "Qty")
    pdf.drawString(120 * mm, y, "Price")
    pdf.drawString(150 * mm, y, "Subtotal")
    y -= 5 * mm
    pdf.line(20 * mm, y, 190 * mm, y)
    y -= 5 * mm

    pdf.setFont("Helvetica", 9)
    for item in order.items.all():
        if y < 30 * mm:
            pdf.showPage()
            y = height - 30 * mm
            pdf.setFont("Helvetica", 9)
        pdf.drawString(20 * mm, y, item.product_name[:40])
        pdf.drawRightString(110 * mm, y, str(item.quantity))
        pdf.drawRightString(135 * mm, y, f"{item.price}")
        pdf.drawRightString(190 * mm, y, f"{item.subtotal}")
        y -= 5 * mm

    y -= 5 * mm
    pdf.line(120 * mm, y, 190 * mm, y)
    y -= 6 * mm
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawRightString(135 * mm, y, "Total:")
    pdf.drawRightString(190 * mm, y, f"{order.total_amount}")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer

