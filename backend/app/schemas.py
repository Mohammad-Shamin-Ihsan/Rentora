"""
Pydantic schemas for the Ratings & Reviews API.
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator


class ReviewCreate(BaseModel):
    booking_id: int
    rating: int = Field(..., ge=1, le=5, description="Star rating from 1 to 5")
    review_text: Optional[str] = Field(None, max_length=2000)

    @field_validator("review_text")
    @classmethod
    def strip_text(cls, v):
        return v.strip() if v else v


class ReviewerOut(BaseModel):
    id: int
    name: str
    # NOTE: your `users` table has no avatar/photo column today, so this
    # is always None for now. If a `product_images`-style table or a
    # `users.avatar_url` column gets added later, wire it in here.
    avatar_url: Optional[str] = None


class ReviewOut(BaseModel):
    id: int
    rating: int
    review_text: Optional[str]
    created_at: datetime
    user: ReviewerOut
    verified_rental: bool = True


class PaginatedReviews(BaseModel):
    items: List[ReviewOut]
    total: int
    page: int
    page_size: int


class RatingSummary(BaseModel):
    product_id: int
    average_rating: float
    review_count: int
    breakdown: dict
