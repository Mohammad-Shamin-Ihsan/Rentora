import { Component } from '@angular/core';
import { ProductReviewsDemoComponent } from './pages/product-reviews-demo/product-reviews-demo.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [ProductReviewsDemoComponent],
  templateUrl: './app.component.html',
})
export class AppComponent {}
