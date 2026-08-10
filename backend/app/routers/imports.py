from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.middleware.auth_middleware import get_current_user

router = APIRouter()

@router.get("/")
async def get_my_bookings(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from sqlalchemy import text
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