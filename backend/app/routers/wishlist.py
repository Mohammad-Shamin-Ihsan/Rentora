from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from app.database import get_db
from app.middleware.auth_middleware import get_current_user

router = APIRouter()


class WishlistAdd(BaseModel):
    product_id: str


@router.get("/")
async def get_my_wishlist(
    current_user: dict = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    result = db.execute(
        text("""
            SELECT w.id as wishlist_id, w.created_at as added_at, p.*
            FROM public.wishlists w
            JOIN public.products p ON w.product_id = p.id
            WHERE w.customer_id = :customer_id
            ORDER BY w.created_at DESC
        """),
        {"customer_id": current_user["id"]}
    ).fetchall()

    return {"data": [dict(row._mapping) for row in result]}


@router.post("/")
async def add_to_wishlist(
    payload:      WishlistAdd,
    current_user: dict = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    product = db.execute(
        text("SELECT id FROM public.products WHERE id = :id"),
        {"id": payload.product_id}
    ).fetchone()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    existing = db.execute(
        text("SELECT id FROM public.wishlists WHERE customer_id = :cid AND product_id = :pid"),
        {"cid": current_user["id"], "pid": payload.product_id}
    ).fetchone()
    if existing:
        return {"message": "Already in wishlist", "already_added": True}

    db.execute(
        text("INSERT INTO public.wishlists (customer_id, product_id) VALUES (:cid, :pid)"),
        {"cid": current_user["id"], "pid": payload.product_id}
    )
    db.commit()

    return {"message": "Added to wishlist", "already_added": False}


@router.delete("/{product_id}")
async def remove_from_wishlist(
    product_id:   str,
    current_user: dict = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    result = db.execute(
        text("""
            DELETE FROM public.wishlists
            WHERE customer_id = :cid AND product_id = :pid
            RETURNING id
        """),
        {"cid": current_user["id"], "pid": product_id}
    ).fetchone()
    db.commit()

    if not result:
        raise HTTPException(status_code=404, detail="Not in wishlist")

    return {"message": "Removed from wishlist"}
