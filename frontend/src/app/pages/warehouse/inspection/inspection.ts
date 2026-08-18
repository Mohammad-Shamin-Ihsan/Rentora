import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';

interface PendingReturn {
  id:                 string;
  product_id:         string;
  product_title:      string;
  images:             string[];
  start_date:         string;
  end_date:           string;
  security_deposit:   number;
  customer_name:      string;
  customer_email:     string;
  status:             string;
}

interface InspectionDraft {
  condition_on_return:   string;
  needs_maintenance:     boolean;
  damage_description:    string;
  damage_penalty_amount: number | null;
}

@Component({
  selector: 'app-inspection',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './inspection.html',
  styleUrls: ['./inspection.css']
})
export class Inspection implements OnInit {

  private apiUrl = environment.apiUrl;

  readonly conditions = ['new', 'excellent', 'good', 'fair', 'damaged'];

  pendingReturns: PendingReturn[] = [];
  isLoading       = true;
  accessDenied    = false;

  openBookingId:  string | null = null;
  drafts:         Record<string, InspectionDraft> = {};
  submittingId:   string | null = null;
  resultMessage:  string | null = null;

  constructor(
    private http: HttpClient,
    private cdr:  ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.loadReturns();
  }

  loadReturns() {
    this.isLoading = true;
    this.http.get<any>(`${this.apiUrl}/warehouse/returns`).subscribe({
      next: (res) => {
        this.pendingReturns = res.data || [];
        this.isLoading       = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        if (err.status === 403) this.accessDenied = true;
        this.isLoading = false;
        this.cdr.detectChanges();
      }
    });
  }

  isOverdue(endDate: string): boolean {
    return new Date(endDate) < new Date(new Date().toDateString());
  }

  selectCondition(bookingId: string, condition: string) {
    this.drafts[bookingId].condition_on_return = condition;
    this.cdr.detectChanges();
  }

  toggleInspect(booking: PendingReturn) {
    this.resultMessage = null;
    if (this.openBookingId === booking.id) {
      this.openBookingId = null;
    } else {
      this.openBookingId = booking.id;
      if (!this.drafts[booking.id]) {
        this.drafts[booking.id] = {
          condition_on_return: 'good',
          needs_maintenance: false,
          damage_description: '',
          damage_penalty_amount: null
        };
      }
    }
    this.cdr.detectChanges();
  }

  submitInspection(booking: PendingReturn) {
    const draft = this.drafts[booking.id];
    if (!draft) return;

    this.submittingId  = booking.id;
    this.resultMessage = null;
    this.cdr.detectChanges();

    this.http.post<any>(`${this.apiUrl}/warehouse/returns`, {
      booking_id:             booking.id,
      condition_on_return:    draft.condition_on_return,
      needs_maintenance:      draft.needs_maintenance,
      damage_description:     draft.damage_description || null,
      damage_penalty_amount:  draft.damage_penalty_amount || 0
    }).subscribe({
      next: (res) => {
        this.submittingId  = null;
        this.openBookingId = null;
        this.resultMessage =
          `"${booking.product_title}" processed — late fee ৳${res.late_fee_amount}, ` +
          `refunded ৳${res.refund_amount}, product is now ${res.product_status}.`;
        this.loadReturns();
        this.cdr.detectChanges();
      },
      error: (err) => {
        alert(err.error?.detail || 'Failed to record inspection.');
        this.submittingId = null;
        this.cdr.detectChanges();
      }
    });
  }

  formatPrice(price: number): string {
    return '৳' + Number(price).toLocaleString('en-BD');
  }

  formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric'
    });
  }
}
