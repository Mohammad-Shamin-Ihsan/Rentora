from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.middleware.auth_middleware import require_role

router = APIRouter()

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