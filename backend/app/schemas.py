"""
Pydantic schemas for the Ratings & Reviews and Waiting List APIs.
"""

from datetime import datetime
from typing import Optional, List, Literal

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


# ── Waiting List Schemas ──────────────────────────────────────────────────────

class WaitingListJoin(BaseModel):
    """Request body for joining a product waiting list."""
    user_email: Optional[str] = Field(
        None,
        description="Email for notification. Falls back to the user's registered email.",
    )


class WaitingListEntry(BaseModel):
    """Represents one row in the waiting_list table."""
    id: int
    product_id: int
    user_id: int
    joined_at: datetime
    notified_at: Optional[datetime]
    status: Literal["pending", "notified", "cancelled"]
    queue_position: Optional[int] = None   # position in the pending queue


class WaitingListStatus(BaseModel):
    """Lightweight status check: is this user on the waiting list for this product?"""
    on_list: bool
    entry: Optional[WaitingListEntry] = None
    pending_count: int   # how many people are ahead (total pending entries)
