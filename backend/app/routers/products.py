from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from app.database import get_db

router = APIRouter()

@router.get("/")
async def get_products(
    category_id: Optional[str] = None,
    brand: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    condition: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 12,
    db: Session = Depends(get_db)
):
    filters = ["p.status = 'available'"]
    params = {}

    if category_id:
        filters.append("p.category_id = :category_id")
        params["category_id"] = category_id
    if brand:
        filters.append("p.brand ILIKE :brand")
        params["brand"] = f"%{brand}%"
    if min_price is not None:
        filters.append("p.rental_price_per_day >= :min_price")
        params["min_price"] = min_price
    if max_price is not None:
        filters.append("p.rental_price_per_day <= :max_price")
        params["max_price"] = max_price
    if condition:
        filters.append("p.condition = :condition")
        params["condition"] = condition
    if search:
        filters.append("p.title ILIKE :search")
        params["search"] = f"%{search}%"

    where_clause = " AND ".join(filters)
    offset = (page - 1) * limit
    params["limit"] = limit
    params["offset"] = offset

    query = text(f"""
        SELECT p.*, c.name as category_name
        FROM public.products p
        LEFT JOIN public.categories c ON p.category_id = c.id
        WHERE {where_clause}
        ORDER BY p.created_at DESC
        LIMIT :limit OFFSET :offset
    """)

    result = db.execute(query, params).fetchall()
    return {
        "data": [dict(row._mapping) for row in result],
        "page": page,
        "limit": limit
    }


@router.get("/{product_id}")
async def get_product(product_id: str, db: Session = Depends(get_db)):
    result = db.execute(
        text("""
            SELECT p.*, c.name as category_name
            FROM public.products p
            LEFT JOIN public.categories c ON p.category_id = c.id
            WHERE p.id = :id
        """),
        {"id": product_id}
    ).fetchone()

    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Product not found")

    return dict(result._mapping)