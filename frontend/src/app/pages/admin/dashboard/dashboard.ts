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

interface Category {
  id:   string;
  name: string;
}

interface Booking {
  id:                     string;
  start_date:             string;
  end_date:               string;
  total_rental_fee:       number;
  tax:                    number;
  security_deposit:       number;
  total_amount:           number;
  status:                 string;
  created_at:             string;
  product_id:             string;
  product_title:          string;
  product_images:         string[] | null;
  customer_id:            string;
  customer_name:          string;
  customer_email:         string;
  return_id:              string | null;
  return_date:            string | null;
  condition_on_return:    string | null;
  needs_maintenance:      boolean | null;
  damage_description:     string | null;
  damage_penalty_amount:  number | null;
  late_fee_amount:        number | null;
}

interface Shipment {
  id:                              string;
  import_request_id:               string;
  status:                          string;
  tracking_notes:                  string | null;
  product_name:                    string;
  product_description:             string | null;
  estimated_budget:                number;
  preferred_rental_duration_days:  number;
  customer_name:                   string;
  customer_email:                  string;
  created_at:                      string;
  updated_at:                      string;
}

interface ReturnForm {
  condition_on_return:   string;
  needs_maintenance:     boolean;
  damage_description:    string;
  damage_penalty_amount: number | null;
}

const EMPTY_RETURN_FORM: ReturnForm = {
  condition_on_return: 'good',
  needs_maintenance: false,
  damage_description: '',
  damage_penalty_amount: 0
};

interface Product {
  id:                    string;
  title:                 string;
  brand:                 string | null;
  description:           string | null;
  category_id:           string | null;
  category_name:         string | null;
  rental_price_per_day:  number;
  security_deposit:      number;
  condition:             string;
  status:                string;
  images:                string[] | null;
}

interface NewProductForm {
  title:                 string;
  brand:                 string;
  description:           string;
  category_id:           string;
  rental_price_per_day:  number | null;
  security_deposit:      number | null;
  condition:              string;
  image_url:             string;
}

const EMPTY_PRODUCT_FORM: NewProductForm = {
  title: '', brand: '', description: '', category_id: '',
  rental_price_per_day: null, security_deposit: null,
  condition: 'good', image_url: ''
};

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

  activeTab: 'imports' | 'analytics' | 'listings' | 'rentals' | 'shipments' = 'imports';

  shipments:        Shipment[] = [];
  isLoadingShipments = true;
  shipmentNoteDrafts: Record<string, string> = {};
  updatingShipmentId: string | null = null;
  readonly cargoStages = ['purchased', 'in_transit', 'customs_cleared', 'arrived'];
  demandRows: DemandRow[] = [];
  isLoadingDemand = true;

  categories: Category[] = [];
  products: Product[] = [];
  isLoadingProducts = true;

  bookings: Booking[] = [];
  isLoadingBookings = true;
  confirmingBookingId: string | null = null;
  returnFormBookingId: string | null = null;
  returnForm: ReturnForm = { ...EMPTY_RETURN_FORM };
  isSubmittingReturn = false;
  bookingActionError = '';

  showNewListingForm = false;
  editingProductId: string | null = null;   // null = creating, set = editing this product
  newProduct: NewProductForm = { ...EMPTY_PRODUCT_FORM };
  isSubmittingProduct = false;
  listingError = '';
  listingSuccess = '';

  constructor(
    private http: HttpClient,
    private cdr:  ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.loadDashboard();
    this.loadImportRequests();
    this.loadDemandAnalytics();
    this.loadCategories();
    this.loadProducts();
    this.loadBookings();
    this.loadShipments();
  }

  loadShipments() {
    this.isLoadingShipments = true;
    this.http.get<any>(`${this.apiUrl}/cargo/shipments`).subscribe({
      next: (res) => {
        this.shipments = res.data || [];
        this.isLoadingShipments = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.isLoadingShipments = false;
        this.cdr.detectChanges();
      }
    });
  }

  cargoStageIndex(status: string): number {
    return this.cargoStages.indexOf(status);
  }

  nextCargoStage(status: string): string | null {
    const i = this.cargoStageIndex(status);
    return i >= 0 && i < this.cargoStages.length - 1 ? this.cargoStages[i + 1] : null;
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

  advanceShipment(shipment: Shipment) {
    const next = this.nextCargoStage(shipment.status);
    if (!next) return;

    this.updatingShipmentId = shipment.id;
    this.cdr.detectChanges();

    this.http.patch<any>(`${this.apiUrl}/cargo/shipments/${shipment.id}`, {
      status:         next,
      tracking_notes: this.shipmentNoteDrafts[shipment.id] || null
    }).subscribe({
      next: (res) => {
        this.updatingShipmentId = null;
        delete this.shipmentNoteDrafts[shipment.id];
        if (res.new_product) {
          alert(`"${res.new_product.title}" has been added to the rental catalog!`);
        }
        this.loadShipments();
        this.loadImportRequests();
        this.cdr.detectChanges();
      },
      error: (err) => {
        alert(err.error?.detail || 'Failed to update shipment.');
        this.updatingShipmentId = null;
        this.cdr.detectChanges();
      }
    });
  }

  loadBookings() {
    this.isLoadingBookings = true;
    this.http.get<any>(`${this.apiUrl}/admin/bookings`).subscribe({
      next: (res) => {
        this.bookings = res.data || [];
        this.isLoadingBookings = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.isLoadingBookings = false;
        this.cdr.detectChanges();
      }
    });
  }

  confirmBooking(booking: Booking) {
    this.bookingActionError = '';
    this.confirmingBookingId = booking.id;
    this.cdr.detectChanges();

    this.http.patch<any>(`${this.apiUrl}/admin/bookings/${booking.id}/status`, {}).subscribe({
      next: () => {
        this.confirmingBookingId = null;
        this.loadBookings();
        this.loadDashboard();
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.bookingActionError = err.error?.detail || 'Failed to confirm booking.';
        this.confirmingBookingId = null;
        this.cdr.detectChanges();
      }
    });
  }

  openReturnForm(booking: Booking) {
    this.bookingActionError = '';
    this.returnFormBookingId = booking.id;
    this.returnForm = { ...EMPTY_RETURN_FORM };
    this.cdr.detectChanges();
  }

  closeReturnForm() {
    this.returnFormBookingId = null;
    this.cdr.detectChanges();
  }

  submitReturn(booking: Booking) {
    this.bookingActionError = '';
    this.isSubmittingReturn = true;
    this.cdr.detectChanges();

    const body = {
      booking_id:            booking.id,
      condition_on_return:   this.returnForm.condition_on_return,
      needs_maintenance:     this.returnForm.needs_maintenance,
      damage_description:    this.returnForm.damage_description.trim() || null,
      damage_penalty_amount: this.returnForm.damage_penalty_amount || 0
    };

    this.http.post<any>(`${this.apiUrl}/warehouse/returns`, body).subscribe({
      next: () => {
        this.isSubmittingReturn = false;
        this.returnFormBookingId = null;
        this.loadBookings();
        this.loadDashboard();
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.bookingActionError = err.error?.detail || 'Failed to log return.';
        this.isSubmittingReturn = false;
        this.cdr.detectChanges();
      }
    });
  }

  loadCategories() {
    this.http.get<any>(`${this.apiUrl}/products/categories`).subscribe({
      next: (res) => {
        this.categories = res.data || [];
        this.cdr.detectChanges();
      }
    });
  }

  loadProducts() {
    this.isLoadingProducts = true;
    this.http.get<any>(`${this.apiUrl}/admin/products`).subscribe({
      next: (res) => {
        this.products = res.data || [];
        this.isLoadingProducts = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.isLoadingProducts = false;
        this.cdr.detectChanges();
      }
    });
  }

  openNewListingForm() {
    this.editingProductId = null;
    this.newProduct = { ...EMPTY_PRODUCT_FORM };
    this.listingError = '';
    this.listingSuccess = '';
    this.showNewListingForm = true;
    this.cdr.detectChanges();
  }

  openEditListingForm(product: Product) {
    this.editingProductId = product.id;
    this.newProduct = {
      title:                product.title,
      brand:                product.brand || '',
      description:          product.description || '',
      category_id:          product.category_id || '',
      rental_price_per_day: Number(product.rental_price_per_day),
      security_deposit:     Number(product.security_deposit),
      condition:            product.condition,
      image_url:            (product.images && product.images.length > 0) ? product.images[0] : ''
    };
    this.listingError = '';
    this.listingSuccess = '';
    this.showNewListingForm = true;
    this.cdr.detectChanges();
  }

  closeNewListingForm() {
    this.showNewListingForm = false;
    this.cdr.detectChanges();
  }

  submitNewListing() {
    this.listingError = '';

    if (!this.newProduct.title.trim()) {
      this.listingError = 'Title is required.';
      return;
    }
    if (!this.newProduct.category_id) {
      this.listingError = 'Please choose a category.';
      return;
    }
    if (!this.newProduct.rental_price_per_day || this.newProduct.rental_price_per_day <= 0) {
      this.listingError = 'Rental price must be greater than zero.';
      return;
    }
    if (this.newProduct.security_deposit === null || this.newProduct.security_deposit < 0) {
      this.listingError = 'Security deposit cannot be negative.';
      return;
    }

    this.isSubmittingProduct = true;
    this.cdr.detectChanges();

    const images = this.newProduct.image_url.trim() ? [this.newProduct.image_url.trim()] : [];
    const body = {
      title:                 this.newProduct.title.trim(),
      brand:                 this.newProduct.brand.trim() || null,
      description:           this.newProduct.description.trim() || null,
      category_id:           this.newProduct.category_id,
      rental_price_per_day:  this.newProduct.rental_price_per_day,
      security_deposit:      this.newProduct.security_deposit,
      condition:             this.newProduct.condition,
      images,
      technical_specifications: {}
    };

    const request$ = this.editingProductId
      ? this.http.patch<any>(`${this.apiUrl}/admin/products/${this.editingProductId}`, body)
      : this.http.post<any>(`${this.apiUrl}/admin/products`, body);

    request$.subscribe({
      next: () => {
        this.isSubmittingProduct = false;
        this.showNewListingForm = false;
        this.listingSuccess = this.editingProductId
          ? `"${this.newProduct.title.trim()}" was updated successfully.`
          : `"${this.newProduct.title.trim()}" was listed successfully.`;
        this.editingProductId = null;
        this.loadProducts();
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.listingError = err.error?.detail || 'Failed to save the listing.';
        this.isSubmittingProduct = false;
        this.cdr.detectChanges();
      }
    });
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

  setTab(tab: 'imports' | 'analytics' | 'listings' | 'rentals' | 'shipments') {
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
      'completed':         'bg-rentora-primary/10 text-rentora-primary',
      'available':         'bg-emerald-400/10 text-emerald-400',
      'booked':            'bg-blue-400/10 text-blue-400',
      'maintenance':       'bg-orange-400/10 text-orange-400',
      'unavailable':       'bg-red-400/10 text-red-400',
      'confirmed':         'bg-yellow-400/10 text-yellow-400',
      'active':            'bg-blue-400/10 text-blue-400',
      'late':              'bg-red-400/10 text-red-400',
      'cancelled':         'bg-gray-400/10 text-gray-400'
    };
    return map[status] || 'bg-gray-400/10 text-gray-400';
  }

  getStatusLabel(status: string): string {
    return status.replace(/_/g, ' ');
  }
}
