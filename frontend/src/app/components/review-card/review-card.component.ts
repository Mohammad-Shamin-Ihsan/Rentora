import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { StarRatingComponent } from '../star-rating/star-rating.component';
import { Review } from '../../models/review.model';

@Component({
  selector: 'app-review-card',
  standalone: true,
  imports: [CommonModule, StarRatingComponent],
  templateUrl: './review-card.component.html',
})
export class ReviewCardComponent {
  @Input({ required: true }) review!: Review;

  get initials(): string {
    const name = this.review?.user?.name ?? '';
    return name
      .split(' ')
      .map((p) => p[0])
      .slice(0, 2)
      .join('')
      .toUpperCase();
  }

  get timeAgo(): string {
    const diffMs = Date.now() - new Date(this.review.created_at).getTime();
    const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    if (days < 1) return 'Today';
    if (days === 1) return '1 day ago';
    if (days < 7) return `${days} days ago`;
    const weeks = Math.floor(days / 7);
    if (weeks < 5) return `${weeks} week${weeks > 1 ? 's' : ''} ago`;
    const months = Math.floor(days / 30);
    return `${months} month${months > 1 ? 's' : ''} ago`;
  }
}
