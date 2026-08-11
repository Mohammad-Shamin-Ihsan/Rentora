// Mirrors backend/app/schemas.py exactly — keep these two files in sync
// whenever the API response shape changes.

export interface Reviewer {
  id: number;
  name: string;
  avatar_url: string | null;
}

export interface Review {
  id: number;
  rating: number;
  review_text: string | null;
  created_at: string;
  user: Reviewer;
  verified_rental: boolean;
}

export interface PaginatedReviews {
  items: Review[];
  total: number;
  page: number;
  page_size: number;
}

export interface RatingSummary {
  product_id: number;
  average_rating: number;
  review_count: number;
  breakdown: Record<string, number>;
}

export interface ReviewCreateRequest {
  booking_id: number;
  rating: number;
  review_text?: string;
}
