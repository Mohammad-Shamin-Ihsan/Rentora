from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.middleware.auth_middleware import get_current_user

router = APIRouter()


class ReviewCreate(BaseModel):
    product_id: str
    booking_id: str
    rating:     int
    review_text: Optional[str] = None


@router.post("/")
async def create_review(
    payload:      ReviewCreate,
    current_user: dict = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    # Validate rating
    if payload.rating < 1 or payload.rating > 5:
        raise HTTPException(
            status_code=400,
            detail="Rating must be between 1 and 5"
        )

    # Get booking and confirm it belongs to the caller
    booking = db.execute(
        text("""
            SELECT customer_id, product_id, status
            FROM public.bookings
            WHERE id = :booking_id
        """),
        {"booking_id": payload.booking_id}
    ).fetchone()

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    if str(booking.customer_id) != str(current_user["id"]):
        raise HTTPException(
            status_code=403,
            detail="You can only review your own rentals"
        )

    if booking.status != "completed":
        raise HTTPException(
            status_code=400,
            detail="You can only review completed rentals"
        )

    # Check if review already exists
    existing = db.execute(
        text("""
            SELECT id FROM public.reviews
            WHERE booking_id = :booking_id
        """),
        {"booking_id": payload.booking_id}
    ).fetchone()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="You have already reviewed this rental"
        )

    # Insert review
    result = db.execute(
        text("""
            INSERT INTO public.reviews
                (product_id, customer_id, booking_id, rating, review_text)
            VALUES
                (:product_id, :customer_id, :booking_id, :rating, :review_text)
            RETURNING *
        """),
        {
            "product_id":  payload.product_id,
            "customer_id": booking.customer_id,
            "booking_id":  payload.booking_id,
            "rating":      payload.rating,
            "review_text": payload.review_text
        }
    )
    db.commit()

    # Update average rating on product
    db.execute(
        text("""
            UPDATE public.products
            SET average_rating = (
                SELECT ROUND(AVG(rating::DECIMAL), 2)
                FROM public.reviews
                WHERE product_id = :product_id
            )
            WHERE id = :product_id
        """),
        {"product_id": payload.product_id}
    )
    db.commit()

    return {
        "message": "Review submitted successfully",
        "review":  dict(result.fetchone()._mapping)
    }


@router.get("/{product_id}")
async def get_product_reviews(
    product_id: str,
    db: Session = Depends(get_db)
):
    result = db.execute(
        text("""
            SELECT
                r.*,
                p.full_name as reviewer_name
            FROM public.reviews r
            LEFT JOIN public.profiles p ON r.customer_id = p.id
            WHERE r.product_id = :product_id
            ORDER BY r.created_at DESC
        """),
        {"product_id": product_id}
    ).fetchall()

    return {"data": [dict(row._mapping) for row in result]}