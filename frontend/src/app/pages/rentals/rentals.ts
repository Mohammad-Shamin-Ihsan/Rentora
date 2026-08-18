import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';

interface Booking {
  id:                string;
  product_id:        string;
  product_title:     string;
  images:            string[];
  start_date:        string;
  end_date:          string;
  total_rental_fee:  number;
  tax:               number;
  security_deposit:  number;
  total_amount:      number;
  status:            string;
  created_at:        string;
}

@Component({
  selector: 'app-rentals',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './rentals.html',
  styleUrls: ['./rentals.css']
})
export class Rentals implements OnInit {

  private apiUrl = environment.apiUrl;

  bookings:      Booking[] = [];
  isLoading      = true;
  errorMessage   = '';
  downloadingId: string | null = null;

  constructor(
    private http: HttpClient,
    private cdr:  ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.loadBookings();
  }

  loadBookings() {
    this.isLoading = true;
    this.http.get<any>(`${this.apiUrl}/bookings/`).subscribe({
      next: (res) => {
        this.bookings  = res.data || [];
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.errorMessage = 'Could not load your rental history.';
        this.isLoading     = false;
        this.cdr.detectChanges();
      }
    });
  }

  downloadInvoice(booking: Booking) {
    this.downloadingId = booking.id;
    this.cdr.detectChanges();

    this.http.get(`${this.apiUrl}/bookings/${booking.id}/invoice`, { responseType: 'blob' }).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a   = document.createElement('a');
        a.href     = url;
        a.download = `rentora-invoice-${booking.id.slice(0, 8)}.pdf`;
        a.click();
        window.URL.revokeObjectURL(url);
        this.downloadingId = null;
        this.cdr.detectChanges();
      },
      error: () => {
        alert('Failed to download invoice. Please try again.');
        this.downloadingId = null;
        this.cdr.detectChanges();
      }
    });
  }

  getProductImage(booking: Booking): string {
    if (!booking.images || booking.images.length === 0) return '';
    const originalUrl = booking.images[0];
    if (originalUrl.includes('unsplash.com')) {
      return `${originalUrl}?auto=format&fit=crop&w=300&q=80`;
    }
    return originalUrl;
  }

  formatPrice(price: number): string {
    return '৳' + Number(price).toLocaleString('en-BD');
  }

  formatDate(dateStr: string): string {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric'
    });
  }

  getStatusColor(status: string): string {
    const map: Record<string, string> = {
      'pending':   'bg-yellow-400/10 text-yellow-400',
      'confirmed': 'bg-blue-400/10 text-blue-400',
      'active':    'bg-emerald-400/10 text-emerald-400',
      'completed': 'bg-rentora-primary/10 text-rentora-primary',
      'cancelled': 'bg-gray-400/10 text-gray-400',
      'late':      'bg-red-400/10 text-red-400'
    };
    return map[status] || 'bg-gray-400/10 text-gray-400';
  }
}
