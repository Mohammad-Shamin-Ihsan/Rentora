"""
Routes for Module 1 / Part 4: Ratings and Reviews.

  POST /products/{product_id}/reviews        -> submit a rating + review
  GET  /products/{product_id}/reviews         -> paginated review list
  GET  /products/{product_id}/reviews/summary -> average rating + breakdown
"""

from fastapi import APIRouter, Depends, Query
from supabase import Client

from .. import schemas
from ..database import get_supabase
from ..crud import reviews as review_crud
from ..auth import get_current_user_id

router = APIRouter(prefix="/products/{product_id}/reviews", tags=["Reviews"])


@router.post("", response_model=schemas.ReviewOut, status_code=201)
def submit_review(
    product_id: int,
    payload: schemas.ReviewCreate,
    supabase: Client = Depends(get_supabase),
    current_user_id: int = Depends(get_current_user_id),
):
    review = review_crud.create_review(supabase, current_user_id, product_id, payload)
    
    created_at_val = review.get("created_at")
    if isinstance(created_at_val, str):
        from datetime import datetime
        try:
            created_at_val = datetime.fromisoformat(created_at_val.replace("Z", "+00:00"))
        except Exception:
            created_at_val = datetime.utcnow()
    elif not created_at_val:
        from datetime import datetime
        created_at_val = datetime.utcnow()

    return schemas.ReviewOut(
        id=review["id"],
        rating=review["rating"],
        review_text=review.get("review_text"),
        created_at=created_at_val,
        user=review_crud._reviewer_out(supabase, review["user_id"]),
        verified_rental=True,
    )



@router.get("", response_model=schemas.PaginatedReviews)
def get_reviews(
    product_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    supabase: Client = Depends(get_supabase),
):
    return review_crud.list_reviews(supabase, product_id, page, page_size)


@router.get("/summary", response_model=schemas.RatingSummary)
def get_rating_summary(product_id: int, supabase: Client = Depends(get_supabase)):
    return review_crud.get_rating_summary(supabase, product_id)

