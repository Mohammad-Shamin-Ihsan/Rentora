import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/services/auth.service';

interface ImportRequest {
  id:                              string;
  product_name:                    string;
  product_description:             string | null;
  preferred_rental_duration_days:  number;
  estimated_budget:                number;
  additional_requirements:         string | null;
  status:                          string;
  admin_notes:                     string | null;
  created_at:                      string;
  shipment_status:                 string | null;
  shipment_notes:                  string | null;
}

@Component({
  selector: 'app-import',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './import.html',
  styleUrls: ['./import.css']
})
export class Import implements OnInit {

  private apiUrl = environment.apiUrl;

  form: FormGroup;
  isSubmitting = false;
  errorMessage = '';
  successMessage = '';

  requests: ImportRequest[] = [];
  isLoadingRequests = true;

  constructor(
    private fb:          FormBuilder,
    private http:        HttpClient,
    private cdr:         ChangeDetectorRef,
    public  authService: AuthService
  ) {
    this.form = this.fb.group({
      product_name:                    ['', [Validators.required, Validators.minLength(3)]],
      product_description:             [''],
      preferred_rental_duration_days:  [7, [Validators.required, Validators.min(1)]],
      estimated_budget:                [null, [Validators.required, Validators.min(1)]],
      additional_requirements:         ['']
    });
  }

  ngOnInit() {
    this.loadRequests();
  }

  get product_name()  { return this.form.get('product_name')!; }
  get preferred_rental_duration_days() { return this.form.get('preferred_rental_duration_days')!; }
  get estimated_budget() { return this.form.get('estimated_budget')!; }

  loadRequests() {
    this.isLoadingRequests = true;
    this.http.get<any>(`${this.apiUrl}/imports/`).subscribe({
      next: (res) => {
        this.requests          = res.data || [];
        this.isLoadingRequests = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.isLoadingRequests = false;
        this.cdr.detectChanges();
      }
    });
  }

  onSubmit() {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.cdr.detectChanges();
      return;
    }

    this.isSubmitting   = true;
    this.errorMessage   = '';
    this.successMessage = '';

    this.http.post<any>(`${this.apiUrl}/imports/`, this.form.value).subscribe({
      next: () => {
        this.isSubmitting   = false;
        this.successMessage = 'Your import request has been submitted! Our team will review it shortly.';
        this.form.reset({ preferred_rental_duration_days: 7, estimated_budget: null });
        this.loadRequests();
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.isSubmitting = false;
        this.errorMessage = err.error?.detail || 'Failed to submit your request. Please try again.';
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

  getStatusColor(status: string): string {
    const map: Record<string, string> = {
      'pending':           'bg-yellow-400/10 text-yellow-400',
      'approved':          'bg-emerald-400/10 text-emerald-400',
      'rejected':          'bg-red-400/10 text-red-400',
      'more_info_needed':  'bg-orange-400/10 text-orange-400',
      'in_progress':       'bg-blue-400/10 text-blue-400',
      'completed':         'bg-rentora-primary/10 text-rentora-primary'
    };
    return map[status] || 'bg-gray-400/10 text-gray-400';
  }

  getStatusLabel(status: string): string {
    return status.replace(/_/g, ' ');
  }

  readonly cargoStages = ['purchased', 'in_transit', 'customs_cleared', 'arrived'];

  cargoStageIndex(status: string | null): number {
    return status ? this.cargoStages.indexOf(status) : -1;
  }

  cargoStageLabel(stage: string): string {
    const map: Record<string, string> = {
      'purchased':       'Purchased',
      'in_transit':      'In Transit',
      'customs_cleared': 'Customs Cleared',
      'arrived':         'Arrived'
    };
    return map[stage] || stage;
  }
}
