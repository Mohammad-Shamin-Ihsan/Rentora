from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
from typing import Optional
import json
from app.database import get_db
from app.middleware.auth_middleware import get_current_user, require_role
from app.utils.notifications import notify_waitlist

router = APIRouter()

VALID_CONDITIONS      = {"new", "excellent", "good", "fair", "damaged"}
VALID_SELLER_STATUSES = {"available", "maintenance"}


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


class ProductStatusUpdate(BaseModel):
    status: str


@router.post("/become")
async def become_seller(
    current_user: dict = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    if current_user["role"] == "seller":
        current_user.pop("password_hash", None)
        return {"message": "You're already a seller.", "user": current_user}

    if current_user["role"] != "customer":
        raise HTTPException(
            status_code=400,
            detail="Only customer accounts can become a seller."
        )

    result = db.execute(
        text("""
            UPDATE public.profiles SET role = 'seller' WHERE id = :id
            RETURNING id, full_name, email, role, phone_number, created_at
        """),
        {"id": current_user["id"]}
    ).fetchone()
    db.commit()

    return {
        "message": "You're now a seller! You can start listing products.",
        "user":    dict(result._mapping)
    }


@router.get("/products")
async def list_my_products(
    current_user: dict = Depends(require_role("seller")),
    db:           Session = Depends(get_db)
):
    result = db.execute(
        text("""
            SELECT p.*, c.name as category_name
            FROM public.products p
            LEFT JOIN public.categories c ON p.category_id = c.id
            WHERE p.seller_id = :seller_id
            ORDER BY p.created_at DESC
        """),
        {"seller_id": current_user["id"]}
    ).fetchall()
    return {"data": [dict(row._mapping) for row in result]}


@router.post("/products")
async def create_product(
    payload:      ProductCreate,
    current_user: dict = Depends(require_role("seller")),
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
                (seller_id, title, brand, description, category_id, rental_price_per_day,
                 security_deposit, condition, status, images, technical_specifications)
            VALUES
                (:seller_id, :title, :brand, :description, :category_id, :rental_price_per_day,
                 :security_deposit, :condition, 'available', :images, CAST(:specs AS jsonb))
            RETURNING *
        """),
        {
            "seller_id":             current_user["id"],
            "title":                 payload.title,
            "brand":                 payload.brand,
            "description":           payload.description or "",
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


@router.patch("/products/{product_id}")
async def update_product(
    product_id:   str,
    payload:      ProductCreate,
    current_user: dict = Depends(require_role("seller")),
    db:           Session = Depends(get_db)
):
    if payload.condition not in VALID_CONDITIONS:
        raise HTTPException(status_code=400, detail=f"Condition must be one of {sorted(VALID_CONDITIONS)}")

    if payload.rental_price_per_day <= 0 or payload.security_deposit < 0:
        raise HTTPException(status_code=400, detail="Price must be positive and deposit cannot be negative")

    existing = db.execute(
        text("SELECT id FROM public.products WHERE id = :id AND seller_id = :seller_id"),
        {"id": product_id, "seller_id": current_user["id"]}
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
            "description":           payload.description or "",
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


@router.delete("/products/{product_id}")
async def delete_product(
    product_id:   str,
    current_user: dict = Depends(require_role("seller")),
    db:           Session = Depends(get_db)
):
    existing = db.execute(
        text("SELECT id FROM public.products WHERE id = :id AND seller_id = :seller_id"),
        {"id": product_id, "seller_id": current_user["id"]}
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")

    try:
        db.execute(
            text("DELETE FROM public.products WHERE id = :id"),
            {"id": product_id}
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="This product can't be deleted because it has booking history. Set it to maintenance instead."
        )

    return {"message": "Product deleted successfully"}


@router.patch("/products/{product_id}/status")
async def update_my_product_status(
    product_id:   str,
    payload:      ProductStatusUpdate,
    current_user: dict = Depends(require_role("seller")),
    db:           Session = Depends(get_db)
):
    if payload.status not in VALID_SELLER_STATUSES:
        raise HTTPException(status_code=400, detail=f"Status must be one of {sorted(VALID_SELLER_STATUSES)}")

    product = db.execute(
        text("SELECT id, status FROM public.products WHERE id = :id AND seller_id = :seller_id"),
        {"id": product_id, "seller_id": current_user["id"]}
    ).fetchone()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.status == "booked":
        raise HTTPException(
            status_code=400,
            detail="This product is currently rented out and its status can't be changed until it's returned."
        )

    result = db.execute(
        text("""
            UPDATE public.products SET status = :status WHERE id = :id
            RETURNING id, title, status
        """),
        {"status": payload.status, "id": product_id}
    ).fetchone()

    notified_count = 0
    if payload.status == "available":
        notified_count = notify_waitlist(db, product_id)

    db.commit()

    return {
        "message":  f"Product status updated to '{payload.status}'",
        "product":  dict(result._mapping),
        "notified": notified_count
    }
