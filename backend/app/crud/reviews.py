"""
CRUD + business logic for Ratings & Reviews using Supabase Python SDK.
"""

from typing import Any, Dict
from fastapi import HTTPException, status
from supabase import Client

from .. import schemas


def create_review(
    supabase: Client, user_id: int, product_id: int, payload: schemas.ReviewCreate
) -> Dict[str, Any]:
    # 1. Check booking existence & status if bookings table is populated
    try:
        booking_res = supabase.table("bookings").select("*").eq("id", payload.booking_id).execute()
        if booking_res.data:
            booking = booking_res.data[0]
            if booking.get("user_id") and booking.get("user_id") != user_id:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN, "You can only review your own bookings."
                )
            if booking.get("status") and booking.get("status") != "completed":
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "You can only leave a review after the booking is completed and returned.",
                )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Notice: Booking validation skipped ({e})")

    # 2. Check for existing review on this booking
    try:
        existing_res = (
            supabase.table("reviews").select("id").eq("booking_id", payload.booking_id).execute()
        )
        if existing_res.data:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "This booking has already been reviewed."
            )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Notice: Duplicate review check skipped ({e})")

    # 3. Insert review row including product_id
    review_data = {
        "booking_id": payload.booking_id,
        "product_id": product_id,
        "user_id": user_id,
        "rating": payload.rating,
        "review_text": payload.review_text,
    }
    insert_res = supabase.table("reviews").insert(review_data).execute()
    if not insert_res.data:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to create review in Supabase."
        )

    return insert_res.data[0]


def _reviewer_out(supabase: Client, user_id: int) -> schemas.ReviewerOut:
    try:
        user_res = supabase.table("users").select("id, name").eq("id", user_id).execute()
        if user_res.data:
            u = user_res.data[0]
            return schemas.ReviewerOut(
                id=u["id"], name=u.get("name") or "Rentora User", avatar_url=None
            )
    except Exception:
        pass
    return schemas.ReviewerOut(id=user_id, name="Rentora User", avatar_url=None)


def get_rating_summary(supabase: Client, product_id: int) -> schemas.RatingSummary:
    # Get direct rating summary from reviews table
    reviews_res = (
        supabase.table("reviews")
        .select("rating")
        .eq("product_id", product_id)
        .execute()
    )

    breakdown = {str(star): 0 for star in range(1, 6)}
    reviews = reviews_res.data or []
    total_reviews = len(reviews)
    sum_ratings = 0

    for r in reviews:
        star_str = str(r.get("rating"))
        if star_str in breakdown:
            breakdown[star_str] += 1
        sum_ratings += int(r.get("rating") or 0)

    avg_rating = round(sum_ratings / total_reviews, 1) if total_reviews > 0 else 0.0

    return schemas.RatingSummary(
        product_id=product_id,
        average_rating=avg_rating,
        review_count=total_reviews,
        breakdown=breakdown,
    )


def list_reviews(
    supabase: Client, product_id: int, page: int = 1, page_size: int = 10
) -> schemas.PaginatedReviews:
    start_index = (page - 1) * page_size
    end_index = start_index + page_size - 1

    res = (
        supabase.table("reviews")
        .select("*", count="exact")
        .eq("product_id", product_id)
        .order("created_at", desc=True)
        .range(start_index, end_index)
        .execute()
    )

    total = res.count if res.count is not None else len(res.data or [])

    items = [
        schemas.ReviewOut(
            id=r["id"],
            rating=r["rating"],
            review_text=r.get("review_text"),
            created_at=r.get("created_at"),
            user=_reviewer_out(supabase, r["user_id"]),
            verified_rental=True,
        )
        for r in (res.data or [])
    ]

    return schemas.PaginatedReviews(items=items, total=total, page=page, page_size=page_size)


