import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  PaginatedReviews,
  RatingSummary,
  ReviewCreateRequest,
  Review,
} from '../models/review.model';

/**
 * Talks to the FastAPI Ratings & Reviews endpoints
 * (backend/app/routers/reviews.py). This is the ONLY place in the
 * frontend that knows the exact URLs — every component calls this
 * service instead of using HttpClient directly.
 */
@Injectable({
  providedIn: 'root',
})
export class ReviewsService {
  private readonly baseUrl = environment.apiBaseUrl;

  constructor(private http: HttpClient) {}

  getRatingSummary(productId: number): Observable<RatingSummary> {
    return this.http.get<RatingSummary>(
      `${this.baseUrl}/products/${productId}/reviews/summary`
    );
  }

  getReviews(
    productId: number,
    page = 1,
    pageSize = 10
  ): Observable<PaginatedReviews> {
    return this.http.get<PaginatedReviews>(
      `${this.baseUrl}/products/${productId}/reviews?page=${page}&page_size=${pageSize}`
    );
  }

  submitReview(
    productId: number,
    payload: ReviewCreateRequest,
    debugUserId: number
  ): Observable<Review> {
    // NOTE: X-Debug-User-Id is a TEMPORARY stand-in for real auth — see
    // backend/app/auth.py. Once Module 1 Part 1's real login exists,
    // swap this header for a real `Authorization: Bearer <token>` and
    // remove the debugUserId parameter — nothing else here changes.
    const headers = new HttpHeaders({
      'X-Debug-User-Id': String(debugUserId),
    });
    return this.http.post<Review>(
      `${this.baseUrl}/products/${productId}/reviews`,
      payload,
      { headers }
    );
  }
}
