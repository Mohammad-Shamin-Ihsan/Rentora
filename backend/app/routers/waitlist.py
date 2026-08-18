from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from app.database import get_db
from app.middleware.auth_middleware import get_current_user

router = APIRouter()


class WaitlistJoin(BaseModel):
    product_id: str


@router.post("/")
async def join_waitlist(
    payload:      WaitlistJoin,
    current_user: dict = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    product = db.execute(
        text("SELECT id, title, status FROM public.products WHERE id = :id"),
        {"id": payload.product_id}
    ).fetchone()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.status == "available":
        raise HTTPException(
            status_code=400,
            detail="This product is already available — no need to join the waitlist"
        )

    existing = db.execute(
        text("""
            SELECT id FROM public.waiting_lists
            WHERE product_id = :product_id AND customer_id = :customer_id AND status = 'waiting'
        """),
        {"product_id": payload.product_id, "customer_id": current_user["id"]}
    ).fetchone()

    if existing:
        raise HTTPException(status_code=400, detail="You're already on the waitlist for this product")

    result = db.execute(
        text("""
            INSERT INTO public.waiting_lists (product_id, customer_id, status)
            VALUES (:product_id, :customer_id, 'waiting')
            RETURNING *
        """),
        {"product_id": payload.product_id, "customer_id": current_user["id"]}
    )
    db.commit()

    return {
        "message": f'Added to the waitlist for "{product.title}"',
        "entry":   dict(result.fetchone()._mapping)
    }


@router.get("/")
async def get_my_waitlist(
    current_user: dict = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    result = db.execute(
        text("""
            SELECT w.*, p.title as product_title, p.images, p.status as product_status
            FROM public.waiting_lists w
            JOIN public.products p ON w.product_id = p.id
            WHERE w.customer_id = :customer_id
            ORDER BY w.joined_at DESC
        """),
        {"customer_id": current_user["id"]}
    ).fetchall()

    return {"data": [dict(row._mapping) for row in result]}


@router.delete("/{entry_id}")
async def leave_waitlist(
    entry_id:     str,
    current_user: dict = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    result = db.execute(
        text("""
            DELETE FROM public.waiting_lists
            WHERE id = :id AND customer_id = :customer_id
            RETURNING id
        """),
        {"id": entry_id, "customer_id": current_user["id"]}
    ).fetchone()
    db.commit()

    if not result:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")

    return {"message": "Removed from waitlist"}
