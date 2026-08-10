from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from app.database import get_db

router = APIRouter()


# ─────────────────────────────────────────
# GET /api/products/categories
# ─────────────────────────────────────────
@router.get("/categories")
async def get_categories(db: Session = Depends(get_db)):
    result = db.execute(
        text("SELECT * FROM public.categories ORDER BY name")
    ).fetchall()
    return {"data": [dict(row._mapping) for row in result]}


# ─────────────────────────────────────────
# GET /api/products/
# Browse + Search + Filter
# ─────────────────────────────────────────
@router.get("/")
async def get_products(
    category_id:  Optional[str]   = None,
    category:     Optional[str]   = None,
    brand:        Optional[str]   = None,
    min_price:    Optional[float] = None,
    max_price:    Optional[float] = None,
    condition:    Optional[str]   = None,
    status:       Optional[str]   = None,
    search:       Optional[str]   = None,
    sort:         Optional[str]   = "newest",
    page:         int             = 1,
    limit:        int             = 12,
    db:           Session         = Depends(get_db)
):
    filters = ["1=1"]
    params  = {}

    # Filter by category id
    if category_id:
        filters.append("p.category_id = :category_id")
        params["category_id"] = category_id

    # Filter by category name
    if category:
        filters.append("c.name ILIKE :category")
        params["category"] = f"%{category}%"

    # Filter by brand
    if brand:
        filters.append("p.brand ILIKE :brand")
        params["brand"] = f"%{brand}%"

    # Filter by price range
    if min_price is not None:
        filters.append("p.rental_price_per_day >= :min_price")
        params["min_price"] = min_price

    if max_price is not None:
        filters.append("p.rental_price_per_day <= :max_price")
        params["max_price"] = max_price

    # Filter by condition
    if condition:
        filters.append("p.condition = :condition")
        params["condition"] = condition

    # Filter by status (default: show only available)
    if status:
        filters.append("p.status = :status")
        params["status"] = status
    else:
        filters.append("p.status = 'available'")

    # Search by title or brand
    if search:
        filters.append(
            "(p.title ILIKE :search OR p.brand ILIKE :search)"
        )
        params["search"] = f"%{search}%"

        # Log search to demand analytics
        try:
            # Check if any product matched
            check = db.execute(
                text("""
                    SELECT COUNT(*) FROM public.products p
                    LEFT JOIN public.categories c ON p.category_id = c.id
                    WHERE p.title ILIKE :term OR p.brand ILIKE :term
                """),
                {"term": f"%{search}%"}
            ).scalar()

            db.execute(
                text("""
                    INSERT INTO public.demand_analytics
                        (search_term, was_available)
                    VALUES (:term, :available)
                """),
                {
                    "term":      search,
                    "available": check > 0
                }
            )
            db.commit()
        except Exception:
            pass

    # Sort
    sort_map = {
        "newest":     "p.created_at DESC",
        "oldest":     "p.created_at ASC",
        "price_asc":  "p.rental_price_per_day ASC",
        "price_desc": "p.rental_price_per_day DESC",
        "rating":     "p.average_rating DESC",
    }
    order_by = sort_map.get(sort, "p.created_at DESC")

    where_clause = " AND ".join(filters)
    offset = (page - 1) * limit
    params["limit"]  = limit
    params["offset"] = offset

    # Get total count
    count_result = db.execute(
        text(f"""
            SELECT COUNT(*)
            FROM public.products p
            LEFT JOIN public.categories c ON p.category_id = c.id
            WHERE {where_clause}
        """),
        params
    ).scalar()

    # Get products
    result = db.execute(
        text(f"""
            SELECT
                p.*,
                c.name as category_name
            FROM public.products p
            LEFT JOIN public.categories c ON p.category_id = c.id
            WHERE {where_clause}
            ORDER BY {order_by}
            LIMIT :limit OFFSET :offset
        """),
        params
    ).fetchall()

    total_pages = (count_result + limit - 1) // limit

    return {
        "data":        [dict(row._mapping) for row in result],
        "total":       count_result,
        "page":        page,
        "limit":       limit,
        "total_pages": total_pages
    }


# ─────────────────────────────────────────
# GET /api/products/{product_id}
# Product detail
# ─────────────────────────────────────────
@router.get("/{product_id}")
async def get_product(product_id: str, db: Session = Depends(get_db)):

    # Get product
    product = db.execute(
        text("""
            SELECT p.*, c.name as category_name
            FROM public.products p
            LEFT JOIN public.categories c ON p.category_id = c.id
            WHERE p.id = :id
        """),
        {"id": product_id}
    ).fetchone()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product_dict = dict(product._mapping)

    # Get reviews
    reviews = db.execute(
        text("""
            SELECT
                r.*,
                pr.full_name as reviewer_name
            FROM public.reviews r
            LEFT JOIN public.profiles pr ON r.customer_id = pr.id
            WHERE r.product_id = :product_id
            ORDER BY r.created_at DESC
        """),
        {"product_id": product_id}
    ).fetchall()

    product_dict["reviews"] = [dict(r._mapping) for r in reviews]

    return product_dict


# ─────────────────────────────────────────
# GET /api/products/{product_id}/availability
# Availability calendar data
# ─────────────────────────────────────────
@router.get("/{product_id}/availability")
async def get_product_availability(
    product_id: str,
    db: Session = Depends(get_db)
):
    # Get blocked dates from bookings
    bookings = db.execute(
        text("""
            SELECT start_date, end_date, status
            FROM public.bookings
            WHERE product_id = :product_id
              AND status IN ('confirmed', 'active', 'pending')
        """),
        {"product_id": product_id}
    ).fetchall()

    # Get maintenance dates
    maintenance = db.execute(
        text("""
            SELECT start_date, end_date, status
            FROM public.product_availability
            WHERE product_id = :product_id
              AND status IN ('maintenance', 'unavailable')
        """),
        {"product_id": product_id}
    ).fetchall()

    booked_ranges = [
        {
            "start":  str(row.start_date),
            "end":    str(row.end_date),
            "reason": "booked"
        }
        for row in bookings
    ]

    maintenance_ranges = [
        {
            "start":  str(row.start_date),
            "end":    str(row.end_date),
            "reason": "maintenance"
        }
        for row in maintenance
    ]

    return {
        "product_id":   product_id,
        "blocked_dates": booked_ranges + maintenance_ranges
    }


# ─────────────────────────────────────────
# GET /api/products/{product_id}/brands
# Get unique brands for filter
# ─────────────────────────────────────────
@router.get("/meta/brands")
async def get_brands(db: Session = Depends(get_db)):
    result = db.execute(
        text("""
            SELECT DISTINCT brand
            FROM public.products
            WHERE brand IS NOT NULL
              AND status = 'available'
            ORDER BY brand
        """)
    ).fetchall()
    return {"data": [row.brand for row in result]}