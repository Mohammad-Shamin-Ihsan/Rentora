import io
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.utils.invoice import build_invoice_pdf
from app.utils.notifications import notify

router = APIRouter()

TAX_RATE = 0.05  # 5%, matches the frontend cost summary


class BookingCreate(BaseModel):
    product_id: str
    start_date: date
    end_date:   date


@router.get("/")
async def get_my_bookings(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    result = db.execute(
        text("""
            SELECT b.*, p.title as product_title, p.images
            FROM public.bookings b
            LEFT JOIN public.products p ON b.product_id = p.id
            WHERE b.customer_id = :customer_id
            ORDER BY b.created_at DESC
        """),
        {"customer_id": current_user["id"]}
    ).fetchall()
    return {"data": [dict(row._mapping) for row in result]}


# ─────────────────────────────────────────
# POST /api/bookings/
# Book a product for a date range.
# Prevents overlapping bookings and computes
# the rental fee / tax / deposit / total server-side.
# ─────────────────────────────────────────
@router.post("/")
async def create_booking(
    payload:      BookingCreate,
    current_user: dict = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    if payload.start_date > payload.end_date:
        raise HTTPException(
            status_code=400,
            detail="Start date must be before or equal to the end date"
        )

    if payload.start_date < date.today():
        raise HTTPException(
            status_code=400,
            detail="Start date cannot be in the past"
        )

    # Fetch product (server is the source of truth for pricing)
    product = db.execute(
        text("""
            SELECT id, title, rental_price_per_day, security_deposit, status
            FROM public.products
            WHERE id = :product_id
        """),
        {"product_id": payload.product_id}
    ).fetchone()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.status != "available":
        raise HTTPException(
            status_code=400,
            detail="This product is not available for booking"
        )

    # Prevent double-booking: reject if any active booking overlaps the range
    overlapping_booking = db.execute(
        text("""
            SELECT id FROM public.bookings
            WHERE product_id = :product_id
              AND status IN ('confirmed', 'active', 'pending')
              AND start_date <= :end_date
              AND end_date   >= :start_date
        """),
        {
            "product_id": payload.product_id,
            "start_date": payload.start_date,
            "end_date":   payload.end_date
        }
    ).fetchone()

    if overlapping_booking:
        raise HTTPException(
            status_code=409,
            detail="Selected dates are no longer available for this product"
        )

    # Reject if the range overlaps a maintenance/unavailable window
    overlapping_maintenance = db.execute(
        text("""
            SELECT id FROM public.product_availability
            WHERE product_id = :product_id
              AND status IN ('maintenance', 'unavailable')
              AND start_date <= :end_date
              AND end_date   >= :start_date
        """),
        {
            "product_id": payload.product_id,
            "start_date": payload.start_date,
            "end_date":   payload.end_date
        }
    ).fetchone()

    if overlapping_maintenance:
        raise HTTPException(
            status_code=409,
            detail="This product is unavailable for part of the selected dates"
        )

    # Rental cost calculation (inclusive of both start and end day)
    rental_days      = (payload.end_date - payload.start_date).days + 1
    rental_fee       = round(float(product.rental_price_per_day) * rental_days, 2)
    tax_amount       = round(rental_fee * TAX_RATE, 2)
    security_deposit = float(product.security_deposit)
    total_amount     = round(rental_fee + tax_amount + security_deposit, 2)

    result = db.execute(
        text("""
            INSERT INTO public.bookings
                (product_id, customer_id, start_date, end_date,
                 total_rental_fee, tax, security_deposit, total_amount, status)
            VALUES
                (:product_id, :customer_id, :start_date, :end_date,
                 :total_rental_fee, :tax, :security_deposit, :total_amount, 'confirmed')
            RETURNING *
        """),
        {
            "product_id":       payload.product_id,
            "customer_id":      current_user["id"],
            "start_date":       payload.start_date,
            "end_date":         payload.end_date,
            "total_rental_fee": rental_fee,
            "tax":              tax_amount,
            "security_deposit": security_deposit,
            "total_amount":     total_amount
        }
    )
    booking = dict(result.fetchone()._mapping)

    # Mock payment: rental fee + tax settle immediately, deposit sits in escrow
    # until the product is returned and inspected (see returns.py for the refund).
    db.execute(
        text("""
            INSERT INTO public.payments (booking_id, amount, type, status, transaction_reference)
            VALUES (:booking_id, :amount, 'rental_fee', 'completed', :ref)
        """),
        {
            "booking_id": booking["id"],
            "amount":     rental_fee + tax_amount,
            "ref":        f"MOCK-RENT-{booking['id']}"
        }
    )
    db.execute(
        text("""
            INSERT INTO public.payments (booking_id, amount, type, status, transaction_reference)
            VALUES (:booking_id, :amount, 'security_deposit', 'escrow', :ref)
        """),
        {
            "booking_id": booking["id"],
            "amount":     security_deposit,
            "ref":        f"MOCK-DEPOSIT-{booking['id']}"
        }
    )

    notify(
        db, current_user["id"], "Booking confirmed",
        f'"{product.title}" is booked for {payload.start_date} to {payload.end_date}. '
        f'Total charged: ৳{total_amount:.2f} (includes a ৳{security_deposit:.2f} refundable deposit).'
    )

    db.commit()

    return {
        "message": "Booking confirmed successfully",
        "booking": booking
    }


# ─────────────────────────────────────────
# GET /api/bookings/{booking_id}/invoice
# Downloadable PDF invoice (owner only)
# ─────────────────────────────────────────
@router.get("/{booking_id}/invoice")
async def get_invoice(
    booking_id:   str,
    current_user: dict = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    booking = db.execute(
        text("""
            SELECT b.*, p.title as product_title, p.brand,
                   pr.full_name as customer_name, pr.email as customer_email
            FROM public.bookings b
            JOIN public.products p ON b.product_id = p.id
            JOIN public.profiles pr ON b.customer_id = pr.id
            WHERE b.id = :id
        """),
        {"id": booking_id}
    ).fetchone()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if str(booking.customer_id) != str(current_user["id"]):
        raise HTTPException(status_code=403, detail="Access denied")

    pdf_bytes = build_invoice_pdf(dict(booking._mapping))

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=rentora-invoice-{booking_id[:8]}.pdf"
        }
    )
