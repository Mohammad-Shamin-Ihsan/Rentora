import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { LucideAngularModule, Star } from 'lucide-angular';

/**
 * StarRating — used in two modes:
 *  - readOnly (default): shows a fixed star rating (review cards, summary header)
 *  - !readOnly: interactive 1-5 picker (used in ReviewForm)
 */
@Component({
  selector: 'app-star-rating',
  standalone: true,
  imports: [CommonModule, LucideAngularModule],
  templateUrl: './star-rating.component.html',
})
export class StarRatingComponent {
  @Input() rating = 0;
  @Input() readOnly = true;
  @Input() size = 18;
  @Output() ratingChange = new EventEmitter<number>();

  readonly starIcon = Star;
  readonly stars = [1, 2, 3, 4, 5];
  hovered = 0;

  get displayRating(): number {
    return this.hovered || this.rating;
  }

  isFilled(star: number): boolean {
    return star <= Math.round(this.displayRating);
  }

  onEnter(star: number): void {
    if (!this.readOnly) this.hovered = star;
  }

  onLeave(): void {
    if (!this.readOnly) this.hovered = 0;
  }

  onClick(star: number): void {
    if (!this.readOnly) this.ratingChange.emit(star);
  }
}
