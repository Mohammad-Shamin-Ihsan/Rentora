import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';

interface ImportRequest {
  id:                              string;
  product_name:                    string;
  product_description:             string | null;
  preferred_rental_duration_days:  number;
  estimated_budget:                number;
  additional_requirements:         string | null;
  status:                          string;
  admin_notes:                     string | null;
  customer_name:                   string;
  customer_email:                  string;
  created_at:                      string;
}

interface DemandRow {
  search_term:        string;
  search_count:       number;
  unavailable_count:  number;
  last_searched_at:   string;
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './dashboard.html',
  styleUrls: ['./dashboard.css']
})
export class Dashboard implements OnInit {

  private apiUrl = environment.apiUrl;

  isLoading      = true;
  accessDenied   = false;

  activeRentals  = 0;
  pendingImports = 0;

  importRequests: ImportRequest[] = [];
  noteDrafts: Record<string, string> = {};
  processingId: string | null = null;

  statusFilter: 'pending' | 'all' = 'pending';

  activeTab: 'imports' | 'analytics' = 'imports';
  demandRows: DemandRow[] = [];
  isLoadingDemand = true;

  constructor(
    private http: HttpClient,
    private cdr:  ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.loadDashboard();
    this.loadImportRequests();
    this.loadDemandAnalytics();
  }

  loadDemandAnalytics() {
    this.isLoadingDemand = true;
    this.http.get<any>(`${this.apiUrl}/admin/demand-analytics`).subscribe({
      next: (res) => {
        this.demandRows       = res.data || [];
        this.isLoadingDemand  = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.isLoadingDemand = false;
        this.cdr.detectChanges();
      }
    });
  }

  get maxSearchCount(): number {
    return Math.max(1, ...this.demandRows.map(r => r.search_count));
  }

  setTab(tab: 'imports' | 'analytics') {
    this.activeTab = tab;
    this.cdr.detectChanges();
  }

  loadDashboard() {
    this.http.get<any>(`${this.apiUrl}/admin/dashboard`).subscribe({
      next: (res) => {
        this.activeRentals  = res.total_active_rentals || 0;
        this.pendingImports = res.pending_imports || 0;
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

  loadImportRequests() {
    this.http.get<any>(`${this.apiUrl}/admin/import-requests`).subscribe({
      next: (res) => {
        this.importRequests = res.data || [];
        this.cdr.detectChanges();
      }
    });
  }

  get visibleRequests(): ImportRequest[] {
    if (this.statusFilter === 'pending') {
      return this.importRequests.filter(r => r.status === 'pending' || r.status === 'more_info_needed');
    }
    return this.importRequests;
  }

  decide(request: ImportRequest, status: 'approved' | 'rejected' | 'more_info_needed') {
    this.processingId = request.id;
    this.cdr.detectChanges();

    this.http.patch<any>(`${this.apiUrl}/admin/import-requests/${request.id}`, {
      status,
      admin_notes: this.noteDrafts[request.id] || null
    }).subscribe({
      next: () => {
        this.processingId = null;
        this.loadImportRequests();
        this.loadDashboard();
        this.cdr.detectChanges();
      },
      error: (err) => {
        alert(err.error?.detail || 'Failed to update request.');
        this.processingId = null;
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
}
