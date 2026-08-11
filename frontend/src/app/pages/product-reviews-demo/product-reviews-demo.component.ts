import { Component } from '@angular/core';
import { ReviewsSectionComponent } from '../../components/reviews-section/reviews-section.component';

@Component({
  selector: 'app-product-reviews-demo',
  standalone: true,
  imports: [ReviewsSectionComponent],
  templateUrl: './product-reviews-demo.component.html',
})
export class ProductReviewsDemoComponent {
  // Matches the seeded test data from sql/D_seed_test_data_v2.sql —
  // update these to match whatever your seed script actually returned.
  productId = 2;
  eligibleBookingId = 1;
  currentUserId = 2;
}
