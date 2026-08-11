import { Component, Input, OnChanges, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { forkJoin } from 'rxjs';
import { StarRatingComponent } from '../star-rating/star-rating.component';
import { ReviewCardComponent } from '../review-card/review-card.component';
import { ReviewFormComponent } from '../review-form/review-form.component';
import { ReviewsService } from '../../services/reviews.service';
import { RatingSummary, Review } from '../../models/review.model';

/**
 * ReviewsSection = the "Customer Feedback" block: big average rating +
 * stars + review count, the optional submit-a-review form, a paginated
 * list of reviews.
 *
 * Usage:
 *   <app-reviews-section
 *     [productId]="product.id"
 *     [eligibleBookingId]="myCompletedUnreviewedBookingId"
 *     [currentUserId]="loggedInUserId">
 *   </app-reviews-section>
 *
 * Pass eligibleBookingId as null/undefined to hide the review form
 * (e.g. a visitor just browsing, or someone who already reviewed).
 */
@Component({
  selector: 'app-reviews-section',
  standalone: true,
  imports: [CommonModule, StarRatingComponent, ReviewCardComponent, ReviewFormComponent],
  templateUrl: './reviews-section.component.html',
})
export class ReviewsSectionComponent implements OnInit, OnChanges {
  @Input({ required: true }) productId!: number;
  @Input() eligibleBookingId: number | null = null;
  @Input() currentUserId = 0;

  summary: RatingSummary | null = null;
  reviews: Review[] = [];
  page = 1;
  pageSize = 5;
  total = 0;
  loading = true;
  errorMessage: string | null = null;

  constructor(private reviewsService: ReviewsService) {}

  ngOnInit(): void {
    this.load();
  }

  ngOnChanges(): void {
    this.load();
  }

  get totalPages(): number {
    return Math.max(1, Math.ceil(this.total / this.pageSize));
  }

  load(): void {
    if (!this.productId) return;
    this.loading = true;
    this.errorMessage = null;

    forkJoin({
      summary: this.reviewsService.getRatingSummary(this.productId),
      reviews: this.reviewsService.getReviews(this.productId, this.page, this.pageSize),
    }).subscribe({
      next: ({ summary, reviews }) => {
        this.summary = summary;
        this.reviews = reviews.items;
        this.total = reviews.total;
        this.loading = false;
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail || "Couldn't load reviews.";
        this.loading = false;
      },
    });
  }

  onReviewSubmitted(): void {
    this.page = 1;
    this.load();
  }

  goToPage(delta: number): void {
    const next = this.page + delta;
    if (next >= 1 && next <= this.totalPages) {
      this.page = next;
      this.load();
    }
  }
}
