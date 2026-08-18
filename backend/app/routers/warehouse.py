from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.middleware.auth_middleware import require_role
from app.utils.notifications import notify, notify_waitlist

router = APIRouter()

VALID_CONDITIONS = {"new", "excellent", "good", "fair", "damaged"}


class ReturnInspectionCreate(BaseModel):
    booking_id:            str
    condition_on_return:   str
    needs_maintenance:     bool = False
    damage_description:    Optional[str] = None
    damage_penalty_amount: float = 0.0


@router.get("/returns")
async def get_pending_returns(
    current_user: dict = Depends(require_role("warehouse_staff", "admin")),
    db:           Session = Depends(get_db)
):
    result = db.execute(
        text("""
            SELECT
                b.*, p.title as product_title, p.images,
                pr.full_name as customer_name, pr.email as customer_email
            FROM public.bookings b
            JOIN public.products p ON b.product_id = p.id
            JOIN public.profiles pr ON b.customer_id = pr.id
            WHERE b.status IN ('confirmed', 'active', 'late')
              AND NOT EXISTS (
                  SELECT 1 FROM public.returns_and_inspections ri WHERE ri.booking_id = b.id
              )
            ORDER BY b.end_date ASC
        """)
    ).fetchall()

    return {"data": [dict(row._mapping) for row in result]}


@router.get("/history")
async def get_inspection_history(
    current_user: dict = Depends(require_role("warehouse_staff", "admin")),
    db:           Session = Depends(get_db)
):
    result = db.execute(
        text("""
            SELECT ri.*, b.product_id, p.title as product_title, pr.full_name as customer_name
            FROM public.returns_and_inspections ri
            JOIN public.bookings b ON ri.booking_id = b.id
            JOIN public.products p ON b.product_id = p.id
            JOIN public.profiles pr ON b.customer_id = pr.id
            ORDER BY ri.created_at DESC
            LIMIT 50
        """)
    ).fetchall()

    return {"data": [dict(row._mapping) for row in result]}


@router.post("/returns")
async def log_return_inspection(
    payload:      ReturnInspectionCreate,
    current_user: dict = Depends(require_role("warehouse_staff", "admin")),
    db:           Session = Depends(get_db)
):
    if payload.condition_on_return not in VALID_CONDITIONS:
        raise HTTPException(status_code=400, detail=f"Condition must be one of {sorted(VALID_CONDITIONS)}")

    if payload.damage_penalty_amount < 0:
        raise HTTPException(status_code=400, detail="Damage penalty cannot be negative")

    booking = db.execute(
        text("""
            SELECT b.*, p.rental_price_per_day, p.title as product_title
            FROM public.bookings b
            JOIN public.products p ON b.product_id = p.id
            WHERE b.id = :id
        """),
        {"id": payload.booking_id}
    ).fetchone()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.status not in ("confirmed", "active", "late"):
        raise HTTPException(status_code=400, detail="This booking has already been returned or was cancelled")

    already_inspected = db.execute(
        text("SELECT id FROM public.returns_and_inspections WHERE booking_id = :id"),
        {"id": payload.booking_id}
    ).fetchone()
    if already_inspected:
        raise HTTPException(status_code=400, detail="This booking has already been inspected")

    # Late fee: a predefined daily rate (the product's own daily rental
    # price) charged for every day past the agreed return date.
    today = date.today()
    late_days = max(0, (today - booking.end_date).days)
    late_fee_amount = round(float(booking.rental_price_per_day) * late_days, 2)

    if payload.damage_penalty_amount > float(booking.security_deposit):
        raise HTTPException(status_code=400, detail="Damage penalty cannot exceed the security deposit")

    db.execute(
        text("""
            INSERT INTO public.returns_and_inspections
                (booking_id, warehouse_staff_id, return_date, condition_on_return,
                 needs_maintenance, damage_description, damage_penalty_amount, late_fee_amount)
            VALUES
                (:booking_id, :staff_id, :return_date, :condition,
                 :needs_maintenance, :damage_description, :damage_penalty, :late_fee)
        """),
        {
            "booking_id":       payload.booking_id,
            "staff_id":         current_user["id"],
            "return_date":      today,
            "condition":        payload.condition_on_return,
            "needs_maintenance": payload.needs_maintenance,
            "damage_description": payload.damage_description,
            "damage_penalty":   payload.damage_penalty_amount,
            "late_fee":         late_fee_amount
        }
    )

    db.execute(
        text("UPDATE public.bookings SET status = 'completed' WHERE id = :id"),
        {"id": payload.booking_id}
    )

    # Security deposit settlement: refund what's left after penalties/late fees
    total_deductions = payload.damage_penalty_amount + late_fee_amount
    refund_amount     = max(0.0, float(booking.security_deposit) - total_deductions)

    db.execute(
        text("""
            UPDATE public.payments SET status = 'refunded'
            WHERE booking_id = :booking_id AND type = 'security_deposit'
        """),
        {"booking_id": payload.booking_id}
    )
    if refund_amount > 0:
        db.execute(
            text("""
                INSERT INTO public.payments (booking_id, amount, type, status, transaction_reference)
                VALUES (:booking_id, :amount, 'refund', 'completed', :ref)
            """),
            {"booking_id": payload.booking_id, "amount": refund_amount, "ref": f"MOCK-REFUND-{payload.booking_id}"}
        )
    if late_fee_amount > 0:
        db.execute(
            text("""
                INSERT INTO public.payments (booking_id, amount, type, status, transaction_reference)
                VALUES (:booking_id, :amount, 'late_fee', 'completed', :ref)
            """),
            {"booking_id": payload.booking_id, "amount": late_fee_amount, "ref": f"MOCK-LATEFEE-{payload.booking_id}"}
        )
    if payload.damage_penalty_amount > 0:
        db.execute(
            text("""
                INSERT INTO public.payments (booking_id, amount, type, status, transaction_reference)
                VALUES (:booking_id, :amount, 'damage_penalty', 'completed', :ref)
            """),
            {"booking_id": payload.booking_id, "amount": payload.damage_penalty_amount, "ref": f"MOCK-PENALTY-{payload.booking_id}"}
        )

    # Inventory status update: back to available (and notify anyone waiting),
    # or into maintenance if it needs repairs.
    new_status = "maintenance" if payload.needs_maintenance else "available"
    db.execute(
        text("UPDATE public.products SET status = :status WHERE id = :id"),
        {"status": new_status, "id": booking.product_id}
    )

    notified_count = 0
    if new_status == "available":
        notified_count = notify_waitlist(db, str(booking.product_id))

    message_parts = [f'"{booking.product_title}" return processed.']
    if late_fee_amount > 0:
        message_parts.append(f"Late fee charged: ৳{late_fee_amount:.2f} ({late_days} day(s) late).")
    if payload.damage_penalty_amount > 0:
        message_parts.append(f"Damage penalty charged: ৳{payload.damage_penalty_amount:.2f}.")
    message_parts.append(f"Deposit refunded: ৳{refund_amount:.2f}.")
    notify(db, str(booking.customer_id), "Return processed", " ".join(message_parts))

    db.commit()

    return {
        "message":         "Return inspection recorded",
        "late_fee_amount": late_fee_amount,
        "refund_amount":   refund_amount,
        "product_status":  new_status,
        "waitlist_notified": notified_count
    }
