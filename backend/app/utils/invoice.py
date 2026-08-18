import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas


def build_invoice_pdf(booking: dict) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    left = 20 * mm
    right = width - 20 * mm
    y = height - 25 * mm

    # Header
    c.setFillColor(colors.HexColor("#7c3aed"))
    c.setFont("Helvetica-Bold", 22)
    c.drawString(left, y, "Rentora")
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 10)
    c.drawRightString(right, y, "RENTAL INVOICE")
    y -= 6 * mm
    c.setFont("Helvetica", 9)
    c.drawRightString(right, y, f"Invoice #{str(booking['id'])[:8].upper()}")
    y -= 12 * mm

    c.setStrokeColor(colors.HexColor("#e5e5e5"))
    c.line(left, y, right, y)
    y -= 10 * mm

    # Customer + booking info
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left, y, "Billed To")
    c.drawString(right - 70 * mm, y, "Booking Details")
    y -= 6 * mm
    c.setFont("Helvetica", 10)
    c.drawString(left, y, booking["customer_name"])
    c.drawString(right - 70 * mm, y, f"Start Date: {booking['start_date']}")
    y -= 5 * mm
    c.drawString(left, y, booking["customer_email"])
    c.drawString(right - 70 * mm, y, f"End Date:   {booking['end_date']}")
    y -= 5 * mm
    c.drawString(right - 70 * mm, y, f"Status:     {booking['status'].capitalize()}")
    y -= 14 * mm

    # Product
    c.setFont("Helvetica-Bold", 11)
    c.drawString(left, y, "Product")
    y -= 6 * mm
    c.setFont("Helvetica", 10)
    brand = f" ({booking['brand']})" if booking.get("brand") else ""
    c.drawString(left, y, f"{booking['product_title']}{brand}")
    y -= 12 * mm

    # Line items table
    rows = [
        ("Description", "Amount (BDT)"),
        ("Rental Fee", f"{booking['total_rental_fee']:.2f}"),
        ("Tax (5%)", f"{booking['tax']:.2f}"),
        ("Security Deposit (refundable)", f"{booking['security_deposit']:.2f}"),
    ]

    c.setFillColor(colors.HexColor("#f5f3ff"))
    c.rect(left, y - 2 * mm, right - left, 8 * mm, fill=1, stroke=0)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left + 2 * mm, y + 1.5 * mm, rows[0][0])
    c.drawRightString(right - 2 * mm, y + 1.5 * mm, rows[0][1])
    y -= 10 * mm

    c.setFont("Helvetica", 10)
    for label, amount in rows[1:]:
        c.drawString(left + 2 * mm, y, label)
        c.drawRightString(right - 2 * mm, y, amount)
        y -= 7 * mm

    c.setStrokeColor(colors.HexColor("#e5e5e5"))
    c.line(left, y, right, y)
    y -= 8 * mm

    c.setFont("Helvetica-Bold", 12)
    c.drawString(left + 2 * mm, y, "Total Due")
    c.drawRightString(right - 2 * mm, y, f"BDT {booking['total_amount']:.2f}")
    y -= 20 * mm

    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(colors.grey)
    c.drawString(left, y, "The security deposit is held in escrow and refunded after a successful return inspection,")
    y -= 4 * mm
    c.drawString(left, y, "minus any late fees or damage penalties assessed at return.")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()
