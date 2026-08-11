import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { StarRatingComponent } from '../star-rating/star-rating.component';
import { ReviewsService } from '../../services/reviews.service';
import { Review } from '../../models/review.model';

@Component({
  selector: 'app-review-form',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, StarRatingComponent],
  templateUrl: './review-form.component.html',
})
export class ReviewFormComponent {
  @Input({ required: true }) productId!: number;
  @Input({ required: true }) bookingId!: number;
  /** Temporary — see reviews.service.ts note on X-Debug-User-Id. */
  @Input({ required: true }) currentUserId!: number;
  @Output() submitted = new EventEmitter<Review>();

  form: FormGroup;
  submitting = false;
  errorMessage: string | null = null;

  constructor(private fb: FormBuilder, private reviewsService: ReviewsService) {
    this.form = this.fb.group({
      rating: [0, [Validators.required, Validators.min(1), Validators.max(5)]],
      reviewText: ['', [Validators.maxLength(2000)]],
    });
  }

  setRating(star: number): void {
    this.form.patchValue({ rating: star });
  }

  onSubmit(): void {
    this.errorMessage = null;

    const rating = this.form.value.rating;
    if (!rating || rating < 1) {
      this.errorMessage = 'Please select a star rating before submitting.';
      return;
    }

    this.submitting = true;
    this.reviewsService
      .submitReview(
        this.productId,
        {
          booking_id: this.bookingId,
          rating,
          review_text: this.form.value.reviewText || undefined,
        },
        this.currentUserId
      )
      .subscribe({
        next: (review) => {
          this.submitting = false;
          this.form.reset({ rating: 0, reviewText: '' });
          this.submitted.emit(review);
        },
        error: (err) => {
          this.submitting = false;
          this.errorMessage =
            err?.error?.detail || 'Something went wrong. Please try again.';
        },
      });
  }
}
