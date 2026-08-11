"""
Models for Module 1 / Part 4: Ratings and Reviews.

With Supabase Python SDK, table structures are handled dynamically via Supabase REST API.
This module defines light model helper containers if needed.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ReviewModel(BaseModel):
    id: Optional[int] = None
    booking_id: int
    product_id: Optional[int] = None
    user_id: int
    rating: int
    review_text: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

