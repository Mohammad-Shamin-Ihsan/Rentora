import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, ActivatedRoute } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/services/auth.service';

interface BlockedDate {
  start:  string;
  end:    string;
  reason: string;
}

interface Review {
  id:            string;
  rating:        number;
  review_text:   string;
  reviewer_name: string;
  created_at:    string;
}

interface Product {
  id:                      string;
  title:                   string;
  brand:                   string;
  description:             string;
  rental_price_per_day:    number;
  security_deposit:        number;
  average_rating:          number;
  images:                  string[];
  condition:               string;
  status:                  string;
  category_name:           string;
  technical_specifications: Record<string, any>;
  reviews:                 Review[];
}

@Component({
  selector: 'app-product-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule],
  templateUrl: './product-detail.html',
  styleUrls: ['./product-detail.css']
})
export class ProductDetail implements OnInit {

  private apiUrl = environment.apiUrl;

  product:     Product | null = null;
  isLoading    = true;
  errorMessage = '';

  // Image gallery
  selectedImageIndex = 0;

  // Calendar
  currentMonth: Date   = new Date();
  blockedDates: BlockedDate[] = [];
  calendarDays: any[]  = [];
  startDate:    string = '';
  endDate:      string = '';
  isSelectingEnd = false;

  // Booking summary
  TAX_RATE = 0.05; // 5%

  // Booking submission
  isBooking       = false;
  bookingError    = '';
  bookingConfirmed = false;

  // Waitlist
  waitlistEmail  = '';
  joinedWaitlist = false;

  // Review
  newRating     = 0;
  newReviewText = '';
  hoverRating   = 0;
  reviewSubmitted = false;

  constructor(
    private http:        HttpClient,
    private route:       ActivatedRoute,
    public  authService: AuthService,
    private cdr:         ChangeDetectorRef
  ) {}

  ngOnInit() {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.loadProduct(id);
      this.loadAvailability(id);
    }
  }

  loadProduct(id: string) {
    this.http.get<Product>(`${this.apiUrl}/products/${id}`).subscribe({
      next: (product) => {
        this.product  = product;
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.errorMessage = 'Product not found.';
        this.isLoading    = false;
        this.cdr.detectChanges();
      }
    });
  }

  loadAvailability(id: string) {
    this.http.get<any>(`${this.apiUrl}/products/${id}/availability`).subscribe({
      next: (res) => {
        this.blockedDates = res.blocked_dates || [];
        this.buildCalendar();
        this.cdr.detectChanges();
      }
    });
  }

  // ── Image Gallery ──────────────────────────
  get currentImage(): string {
    if (!this.product?.images?.length) return '';
    const originalUrl = this.product.images[this.selectedImageIndex];
    if (originalUrl.includes('unsplash.com')) {
      return `${originalUrl}?auto=format&fit=crop&w=800&q=85`; // Slightly larger for detail view
    }
    return originalUrl;
  }

  selectImage(index: number) {
    this.selectedImageIndex = index;
  }

  // ── Calendar ───────────────────────────────

  buildCalendar() {
    const year  = this.currentMonth.getFullYear();
    const month = this.currentMonth.getMonth();

    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    const days: any[] = [];

    // Empty cells before first day
    for (let i = 0; i < firstDay; i++) {
      days.push({ day: null, date: null, isBlocked: false, reason: '' });
    }

    // Actual days
    for (let d = 1; d <= daysInMonth; d++) {
      const date       = new Date(year, month, d);
      const dateStr    = this.toDateStr(date);
      const today      = new Date();
      today.setHours(0, 0, 0, 0);
      const isPast     = date < today;
      const blockInfo  = this.getBlockInfo(dateStr);

      days.push({
        day:       d,
        date:      dateStr,
        isBlocked: isPast || !!blockInfo,
        isPast,
        reason:    blockInfo?.reason || '',
        isStart:   dateStr === this.startDate,
        isEnd:     dateStr === this.endDate,
        isInRange: this.isInRange(dateStr)
      });
    }

    this.calendarDays = days;
  }

  getBlockInfo(dateStr: string): BlockedDate | null {
    for (const block of this.blockedDates) {
      if (dateStr >= block.start && dateStr <= block.end) {
        return block;
      }
    }
    return null;
  }

  isInRange(dateStr: string): boolean {
    if (!this.startDate || !this.endDate) return false;
    return dateStr > this.startDate && dateStr < this.endDate;
  }

  onDayClick(day: any) {
    if (!day.date || day.isBlocked) return;

    if (!this.startDate || (this.startDate && this.endDate)) {
      // Start fresh selection
      this.startDate = day.date;
      this.endDate   = '';
      this.isSelectingEnd = true;
      this.bookingConfirmed = false;
      this.bookingError     = '';
    } else if (this.isSelectingEnd) {
      if (day.date < this.startDate) {
        // Clicked before start — reset
        this.startDate = day.date;
        this.endDate   = '';
      } else {
        // Check no blocked dates in range
        if (this.hasBlockedInRange(this.startDate, day.date)) {
          alert('Selected range includes unavailable dates. Please choose different dates.');
          return;
        }
        this.endDate        = day.date;
        this.isSelectingEnd = false;
      }
    }

    this.buildCalendar();
  }

  hasBlockedInRange(start: string, end: string): boolean {
    for (const block of this.blockedDates) {
      if (start <= block.end && end >= block.start) return true;
    }
    return false;
  }

  prevMonth() {
    this.currentMonth = new Date(
      this.currentMonth.getFullYear(),
      this.currentMonth.getMonth() - 1
    );
    this.buildCalendar();
  }

  nextMonth() {
    this.currentMonth = new Date(
      this.currentMonth.getFullYear(),
      this.currentMonth.getMonth() + 1
    );
    this.buildCalendar();
  }

  toDateStr(date: Date): string {
    return date.toISOString().split('T')[0];
  }

  get monthLabel(): string {
    return this.currentMonth.toLocaleDateString('en-US', {
      month: 'long', year: 'numeric'
    });
  }

  get rentalDays(): number {
    if (!this.startDate || !this.endDate) return 0;
    const start = new Date(this.startDate);
    const end   = new Date(this.endDate);
    return Math.ceil(
      (end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)
    ) + 1;
  }

  get rentalFee(): number {
    if (!this.product) return 0;
    return this.product.rental_price_per_day * this.rentalDays;
  }

  get taxAmount(): number {
    return this.rentalFee * this.TAX_RATE;
  }

  get totalAmount(): number {
    if (!this.product) return 0;
    return this.rentalFee + this.taxAmount + this.product.security_deposit;
  }

  // ── Booking ────────────────────────────────

  reserveNow() {
    if (!this.product || !this.startDate || !this.endDate) return;

    this.isBooking       = true;
    this.bookingError    = '';
    this.bookingConfirmed = false;

    const payload = {
      product_id: this.product.id,
      start_date: this.startDate,
      end_date:   this.endDate
    };

    this.http.post<any>(`${this.apiUrl}/bookings/`, payload).subscribe({
      next: () => {
        this.isBooking        = false;
        this.bookingConfirmed = true;
        this.startDate = '';
        this.endDate   = '';
        this.cdr.detectChanges();

        // Refresh availability so the calendar reflects the new booking
        this.loadAvailability(this.product!.id);
      },
      error: (err) => {
        this.isBooking     = false;
        this.bookingError  = err.error?.detail || 'Failed to create booking. Please try again.';
        this.cdr.detectChanges();
      }
    });
  }

  formatPrice(price: number): string {
    return '৳' + price.toLocaleString('en-BD');
  }

  formatDate(dateStr: string): string {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric'
    });
  }

  // ── Waitlist ──────────────────────────────

  joinWaitlist() {
    if (!this.waitlistEmail) return;
    // Will connect to booking/waitlist endpoint in Module 2
    this.joinedWaitlist = true;
  }

  // ── Reviews ───────────────────────────────

  setRating(rating: number) {
    this.newRating = rating;
  }

  submitReview() {
    if (this.newRating === 0 || !this.product) return;

    const productId = this.product.id;

    // Find one of the current user's completed bookings for this product
    this.http.get<any>(`${this.apiUrl}/bookings/`).subscribe({
      next: (res) => {
        const bookings = res.data || [];
        const completedBooking = bookings.find(
          (b: any) => b.product_id === productId && b.status === 'completed'
        );

        if (!completedBooking) {
          alert('You can only review products from a completed rental.');
          return;
        }

        const payload = {
          product_id: productId,
          booking_id: completedBooking.id,
          rating: this.newRating,
          review_text: this.newReviewText
        };

        this.http.post<any>(`${this.apiUrl}/reviews/`, payload).subscribe({
          next: () => {
            this.reviewSubmitted = true;
            this.cdr.detectChanges();
            // Reload product details to show the new review instantly
            this.loadProduct(productId);
          },
          error: (err) => {
            alert(err.error?.detail || 'Failed to submit review. Note: You can only review completed rentals.');
          }
        });
      },
      error: () => {
        alert('Could not verify your rental history. Please try again.');
      }
    });
  }

  getStarClass(star: number): string {
    const filled = star <= (this.hoverRating || this.newRating);
    return filled ? 'text-yellow-400' : 'text-rentora-border';
  }

  getConditionLabel(condition: string): string {
    const map: Record<string, string> = {
      'new':       '✨ New',
      'excellent': '⭐ Excellent',
      'good':      '👍 Good',
      'fair':      '⚠️ Fair',
      'damaged':   '⛔ Damaged'
    };
    return map[condition] || condition;
  }

  get specsEntries(): { key: string; value: any }[] {
    if (!this.product?.technical_specifications) return [];
    return Object.entries(this.product.technical_specifications)
      .map(([key, value]) => ({ key, value }));
  }
}