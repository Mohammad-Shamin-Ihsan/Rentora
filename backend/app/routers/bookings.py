from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from app.database import get_db
from app.middleware.auth_middleware import get_current_user

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
            SELECT id, rental_price_per_day, security_deposit, status
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
                 rental_fee, tax_amount, security_deposit, total_amount, status)
            VALUES
                (:product_id, :customer_id, :start_date, :end_date,
                 :rental_fee, :tax_amount, :security_deposit, :total_amount, 'confirmed')
            RETURNING *
        """),
        {
            "product_id":       payload.product_id,
            "customer_id":      current_user["id"],
            "start_date":       payload.start_date,
            "end_date":         payload.end_date,
            "rental_fee":       rental_fee,
            "tax_amount":       tax_amount,
            "security_deposit": security_deposit,
            "total_amount":     total_amount
        }
    )
    db.commit()

    return {
        "message": "Booking confirmed successfully",
        "booking": dict(result.fetchone()._mapping)
    }
