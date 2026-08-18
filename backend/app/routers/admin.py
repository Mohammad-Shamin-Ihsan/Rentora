from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from app.database import get_db
from app.middleware.auth_middleware import require_role
from app.utils.notifications import notify_waitlist

router = APIRouter()

VALID_PRODUCT_STATUSES = {"available", "booked", "maintenance", "unavailable"}


class ProductStatusUpdate(BaseModel):
    status: str

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