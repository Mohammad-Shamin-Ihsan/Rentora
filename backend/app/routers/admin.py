from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional
import json
from app.database import get_db
from app.middleware.auth_middleware import require_role
from app.utils.notifications import notify_waitlist, notify

router = APIRouter()

VALID_PRODUCT_STATUSES = {"available", "booked", "maintenance", "unavailable"}
VALID_IMPORT_DECISIONS = {"approved", "rejected", "more_info_needed"}
VALID_CONDITIONS       = {"new", "mint", "excellent", "good", "fair"}


class ProductStatusUpdate(BaseModel):
    status: str


class ImportDecision(BaseModel):
    status:      str
    admin_notes: str | None = None


class ProductCreate(BaseModel):
    title:                    str
    brand:                    Optional[str] = None
    description:              Optional[str] = None
    category_id:              str
    rental_price_per_day:     float
    security_deposit:         float
    condition:                str = "good"
    images:                   list[str] = []
    technical_specifications: dict = {}

@router.get("/dashboard")
async def get_dashboard(
    current_user: dict = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    active_rentals = db.execute(
        text("SELECT COUNT(*) FROM public.bookings WHERE status = 'active'")
    ).scalar()

    pending_imports = db.execute(
        text("SELECT COUNT(*) FROM public.import_requests WHERE status = 'pending'")
    ).scalar()

    return {
        "total_active_rentals": active_rentals,
        "pending_imports": pending_imports
    }

@router.get("/import-requests")
async def get_all_import_requests(
    current_user: dict = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    result = db.execute(
        text("""
            SELECT ir.*, p.full_name as customer_name, p.email as customer_email
            FROM public.import_requests ir
            LEFT JOIN public.profiles p ON ir.customer_id = p.id
            ORDER BY ir.created_at DESC
        """)
    ).fetchall()
    return {"data": [dict(row._mapping) for row in result]}


@router.patch("/import-requests/{request_id}")
async def decide_import_request(
    request_id:   str,
    payload:      ImportDecision,
    current_user: dict = Depends(require_role("admin")),
    db:           Session = Depends(get_db)
):
    if payload.status not in VALID_IMPORT_DECISIONS:
        raise HTTPException(status_code=400, detail=f"Status must be one of {sorted(VALID_IMPORT_DECISIONS)}")

    request_row = db.execute(
        text("SELECT * FROM public.import_requests WHERE id = :id"),
        {"id": request_id}
    ).fetchone()

    if not request_row:
        raise HTTPException(status_code=404, detail="Import request not found")

    result = db.execute(
        text("""
            UPDATE public.import_requests
            SET status = :status, admin_notes = :admin_notes
            WHERE id = :id
            RETURNING *
        """),
        {"status": payload.status, "admin_notes": payload.admin_notes, "id": request_id}
    ).fetchone()

    # Approval kicks off cargo tracking for this request
    if payload.status == "approved":
        db.execute(
            text("""
                INSERT INTO public.cargo_shipments (import_request_id, status)
                VALUES (:import_request_id, 'purchased')
            """),
            {"import_request_id": request_id}
        )

    status_messages = {
        "approved":         f'Your import request for "{request_row.product_name}" was approved! We\'re now sourcing it.',
        "rejected":         f'Your import request for "{request_row.product_name}" was declined.',
        "more_info_needed": f'We need more information about your import request for "{request_row.product_name}".',
    }
    notify(db, str(request_row.customer_id), "Import request update", status_messages[payload.status])

    db.commit()

    return {
        "message": f"Import request {payload.status}",
        "request": dict(result._mapping)
    }


@router.get("/demand-analytics")
async def get_demand_analytics(
    current_user: dict = Depends(require_role("admin")),
    db:           Session = Depends(get_db)
):
    # Frequently searched-for terms, prioritizing ones that came up
    # empty (unavailable locally) - the strongest signal for what to import next.
    result = db.execute(
        text("""
            SELECT
                search_term,
                COUNT(*) as search_count,
                COUNT(*) FILTER (WHERE was_available = false) as unavailable_count,
                MAX(searched_at) as last_searched_at
            FROM public.demand_analytics
            GROUP BY search_term
            ORDER BY unavailable_count DESC, search_count DESC
            LIMIT 25
        """)
    ).fetchall()

    return {"data": [dict(row._mapping) for row in result]}


@router.post("/products")
async def create_product(
    payload:      ProductCreate,
    current_user: dict = Depends(require_role("admin")),
    db:           Session = Depends(get_db)
):
    if payload.condition not in VALID_CONDITIONS:
        raise HTTPException(status_code=400, detail=f"Condition must be one of {sorted(VALID_CONDITIONS)}")

    if payload.rental_price_per_day <= 0 or payload.security_deposit < 0:
        raise HTTPException(status_code=400, detail="Price must be positive and deposit cannot be negative")

    category = db.execute(
        text("SELECT id FROM public.categories WHERE id = :id"),
        {"id": payload.category_id}
    ).fetchone()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    result = db.execute(
        text("""
            INSERT INTO public.products
                (title, brand, description, category_id, rental_price_per_day,
                 security_deposit, condition, status, images, technical_specifications)
            VALUES
                (:title, :brand, :description, :category_id, :rental_price_per_day,
                 :security_deposit, :condition, 'available', :images, CAST(:specs AS jsonb))
            RETURNING *
        """),
        {
            "title":                 payload.title,
            "brand":                 payload.brand,
            "description":           payload.description,
            "category_id":           payload.category_id,
            "rental_price_per_day":  payload.rental_price_per_day,
            "security_deposit":      payload.security_deposit,
            "condition":             payload.condition,
            "images":                payload.images,
            "specs":                 json.dumps(payload.technical_specifications),
        }
    )
    db.commit()

    return {
        "message": "Product listed successfully",
        "product": dict(result.fetchone()._mapping)
    }


@router.get("/products")
async def list_all_products(
    current_user: dict = Depends(require_role("admin")),
    db:           Session = Depends(get_db)
):
    # Unlike the public GET /api/products/ (which defaults to
    # status='available' only), this returns every product regardless
    # of status, so admins can find and edit anything they've listed.
    result = db.execute(
        text("""
            SELECT p.*, c.name as category_name
            FROM public.products p
            LEFT JOIN public.categories c ON p.category_id = c.id
            ORDER BY p.created_at DESC
        """)
    ).fetchall()
    return {"data": [dict(row._mapping) for row in result]}


@router.patch("/products/{product_id}")
async def update_product(
    product_id:   str,
    payload:      ProductCreate,
    current_user: dict = Depends(require_role("admin")),
    db:           Session = Depends(get_db)
):
    if payload.condition not in VALID_CONDITIONS:
        raise HTTPException(status_code=400, detail=f"Condition must be one of {sorted(VALID_CONDITIONS)}")

    if payload.rental_price_per_day <= 0 or payload.security_deposit < 0:
        raise HTTPException(status_code=400, detail="Price must be positive and deposit cannot be negative")

    existing = db.execute(
        text("SELECT id FROM public.products WHERE id = :id"),
        {"id": product_id}
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")

    category = db.execute(
        text("SELECT id FROM public.categories WHERE id = :id"),
        {"id": payload.category_id}
    ).fetchone()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    result = db.execute(
        text("""
            UPDATE public.products
            SET title = :title,
                brand = :brand,
                description = :description,
                category_id = :category_id,
                rental_price_per_day = :rental_price_per_day,
                security_deposit = :security_deposit,
                condition = :condition,
                images = :images,
                technical_specifications = CAST(:specs AS jsonb)
            WHERE id = :id
            RETURNING *
        """),
        {
            "title":                 payload.title,
            "brand":                 payload.brand,
            "description":           payload.description,
            "category_id":           payload.category_id,
            "rental_price_per_day":  payload.rental_price_per_day,
            "security_deposit":      payload.security_deposit,
            "condition":             payload.condition,
            "images":                payload.images,
            "specs":                 json.dumps(payload.technical_specifications),
            "id":                    product_id,
        }
    )
    db.commit()

    return {
        "message": "Product updated successfully",
        "product": dict(result.fetchone()._mapping)
    }


@router.get("/bookings")
async def list_all_bookings(
    current_user: dict = Depends(require_role("admin")),
    db:           Session = Depends(get_db)
):
    # Full rental history for the admin dashboard: every booking, who it's
    # for, what was rented, and (via the LEFT JOIN) whether/how it was
    # returned. ri.id IS NULL means "not returned yet".
    result = db.execute(
        text("""
            SELECT
                b.id, b.start_date, b.end_date, b.total_rental_fee, b.tax,
                b.security_deposit, b.total_amount, b.status, b.created_at,
                p.id as product_id, p.title as product_title, p.images as product_images,
                pr.id as customer_id, pr.full_name as customer_name, pr.email as customer_email,
                ri.id as return_id, ri.return_date, ri.condition_on_return,
                ri.needs_maintenance, ri.damage_description,
                ri.damage_penalty_amount, ri.late_fee_amount
            FROM public.bookings b
            JOIN public.products p ON b.product_id = p.id
            JOIN public.profiles pr ON b.customer_id = pr.id
            LEFT JOIN public.returns_and_inspections ri ON ri.booking_id = b.id
            ORDER BY b.created_at DESC
        """)
    ).fetchall()

    return {"data": [dict(row._mapping) for row in result]}


@router.patch("/bookings/{booking_id}/status")
async def confirm_booking(
    booking_id:   str,
    current_user: dict = Depends(require_role("admin")),
    db:           Session = Depends(get_db)
):
    # The only transition exposed here is "Confirm Booking": moving a
    # newly-placed booking from 'confirmed' to 'active', i.e. the admin
    # is acknowledging the rental has started / item has gone out.
    booking = db.execute(
        text("SELECT id, status FROM public.bookings WHERE id = :id"),
        {"id": booking_id}
    ).fetchone()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.status != "confirmed":
        raise HTTPException(
            status_code=400,
            detail=f"Only bookings with status 'confirmed' can be started. This booking is '{booking.status}'."
        )

    result = db.execute(
        text("""
            UPDATE public.bookings SET status = 'active' WHERE id = :id
            RETURNING id, status
        """),
        {"id": booking_id}
    ).fetchone()

    db.commit()

    return {
        "message": "Booking confirmed and marked active",
        "booking": dict(result._mapping)
    }


@router.patch("/products/{product_id}/status")
async def update_product_status(
    product_id:   str,
    payload:      ProductStatusUpdate,
    current_user: dict = Depends(require_role("admin")),
    db:           Session = Depends(get_db)
):
    if payload.status not in VALID_PRODUCT_STATUSES:
        raise HTTPException(status_code=400, detail=f"Status must be one of {sorted(VALID_PRODUCT_STATUSES)}")

    result = db.execute(
        text("""
            UPDATE public.products SET status = :status WHERE id = :id
            RETURNING id, title, status
        """),
        {"status": payload.status, "id": product_id}
    ).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Product not found")

    notified_count = 0
    if payload.status == "available":
        notified_count = notify_waitlist(db, product_id)

    db.commit()

    return {
        "message":  f"Product status updated to '{payload.status}'",
        "product":  dict(result._mapping),
        "notified": notified_count
    }