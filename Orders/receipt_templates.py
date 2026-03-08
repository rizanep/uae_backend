from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
import qrcode
from reportlab.lib.utils import ImageReader


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


def render_admin_receipt_pdf(order):
    """
    Render a detailed PDF receipt for admin use, including all order details, QR code, etc.
    """
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(f"Order ID: {order.id}")
    qr.make(fit=True)
    qr_img = qr.make_image(fill='black', back_color='white')
    
    # Convert QR code to bytes for reportlab
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)
    qr_reader = ImageReader(qr_buffer)

    y = height - 30 * mm
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(20 * mm, y, "Order Receipt")
    y -= 15 * mm

    # QR Code on the right
    pdf.drawImage(qr_reader, 140 * mm, y - 30 * mm, width=40 * mm, height=40 * mm)

    pdf.setFont("Helvetica", 10)
    pdf.drawString(20 * mm, y, f"Order ID: {order.id}")
    y -= 8 * mm
    pdf.drawString(20 * mm, y, f"Date: {order.created_at.strftime('%Y-%m-%d %H:%M')}")
    y -= 8 * mm
    pdf.drawString(20 * mm, y, f"Status: {order.get_status_display()}")
    y -= 10 * mm

    # Customer Information
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(20 * mm, y, "Customer Information")
    y -= 8 * mm
    pdf.setFont("Helvetica", 10)
    user = order.user
    customer_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or str(user)
    pdf.drawString(20 * mm, y, f"Name: {customer_name}")
    y -= 6 * mm
    if user.email:
        pdf.drawString(20 * mm, y, f"Email: {user.email}")
        y -= 6 * mm
    if user.phone_number:
        pdf.drawString(20 * mm, y, f"Phone: {user.phone_number}")
        y -= 8 * mm

    # Shipping Address
    if order.shipping_address:
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(20 * mm, y, "Shipping Address")
        y -= 8 * mm
        pdf.setFont("Helvetica", 10)
        address = order.shipping_address
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

    # Delivery Information
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(20 * mm, y, "Delivery Information")
    y -= 8 * mm
    pdf.setFont("Helvetica", 10)
    if order.preferred_delivery_date:
        pdf.drawString(20 * mm, y, f"Preferred Date: {order.preferred_delivery_date}")
        y -= 6 * mm
    if order.preferred_delivery_slot:
        pdf.drawString(20 * mm, y, f"Preferred Slot: {order.preferred_delivery_slot}")
        y -= 6 * mm
    if order.delivery_notes:
        pdf.drawString(20 * mm, y, f"Notes: {order.delivery_notes}")
        y -= 8 * mm

    # Payment Information
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(20 * mm, y, "Payment Information")
    y -= 8 * mm
    pdf.setFont("Helvetica", 10)
    payment = getattr(order, 'payment', None)
    if payment:
        pdf.drawString(20 * mm, y, f"Payment Method: {payment.get_payment_method_display()}")
        y -= 6 * mm
        pdf.drawString(20 * mm, y, f"Payment Status: {payment.get_status_display()}")
        y -= 6 * mm
        pdf.drawString(20 * mm, y, f"Amount: AED {payment.amount}")
        y -= 6 * mm
        if payment.transaction_id:
            pdf.drawString(20 * mm, y, f"Transaction ID: {payment.transaction_id}")
            y -= 8 * mm
    else:
        pdf.drawString(20 * mm, y, "Payment: Not processed")
        y -= 8 * mm

    # Items
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(20 * mm, y, "Order Items")
    y -= 8 * mm

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
        pdf.drawRightString(135 * mm, y, f"AED {item.price}")
        pdf.drawRightString(190 * mm, y, f"AED {item.subtotal}")
        y -= 5 * mm

    y -= 5 * mm
    pdf.line(120 * mm, y, 190 * mm, y)
    y -= 6 * mm
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawRightString(135 * mm, y, "Total:")
    pdf.drawRightString(190 * mm, y, f"AED {order.total_amount}")
    if order.tip_amount > 0:
        y -= 6 * mm
        pdf.drawRightString(135 * mm, y, "Tip:")
        pdf.drawRightString(190 * mm, y, f"AED {order.tip_amount}")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer

