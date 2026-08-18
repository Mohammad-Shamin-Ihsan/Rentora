import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, ActivatedRoute, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { debounceTime, distinctUntilChanged, Subject } from 'rxjs';
import { AuthService } from '../../core/services/auth.service';

interface Product {
  id: string;
  title: string;
  brand: string;
  rental_price_per_day: number;
  security_deposit: number;
  average_rating: number;
  images: string[];
  condition: string;
  status: string;
  category_name: string;
  description: string;
}

interface Category {
  id: string;
  name: string;
}

@Component({
  selector: 'app-browse',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule],
  templateUrl: './browse.html',
  styleUrls: ['./browse.css']
})
export class Browse implements OnInit {

  private apiUrl = environment.apiUrl;

  // Products
  products:    Product[] = [];
  isLoading    = true;
  totalResults = 0;
  totalPages   = 1;
  currentPage  = 1;

  // Categories
  categories: Category[] = [];
  brands:     string[]   = [];

  // Filters
  searchQuery     = '';
  selectedCategory = '';
  selectedBrand   = '';
  minPrice:  number | null = null;
  maxPrice:  number | null = null;
  selectedCondition = '';
  sortBy = 'newest';

  // Search debounce
  private searchSubject = new Subject<string>();

  // UI state
  isMobileFilterOpen = false;

  // Wishlist
  wishlistIds = new Set<string>();

  conditions = [
    { value: '',          label: 'Any Condition' },
    { value: 'new',       label: 'New' },
    { value: 'excellent', label: 'Excellent' },
    { value: 'good',      label: 'Good' },
    { value: 'fair',      label: 'Fair' }
  ];

  sortOptions = [
    { value: 'newest',     label: 'Newest First' },
    { value: 'price_asc',  label: 'Price: Low to High' },
    { value: 'price_desc', label: 'Price: High to Low' },
    { value: 'rating',     label: 'Top Rated' }
  ];

  constructor(
    private http:        HttpClient,
    private route:       ActivatedRoute,
    private router:      Router,
    private cdr:         ChangeDetectorRef,
    public  authService: AuthService
  ) {}

  ngOnInit() {
    this.loadCategories();
    this.loadBrands();
    this.loadWishlist();

    // Read query params from URL
    this.route.queryParams.subscribe(params => {
      if (params['category'])  this.selectedCategory = params['category'];
      if (params['search'])    this.searchQuery      = params['search'];
      this.loadProducts();
    });

    // Debounce search input
    this.searchSubject.pipe(
      debounceTime(400),
      distinctUntilChanged()
    ).subscribe(() => {
      this.currentPage = 1;
      this.loadProducts();
    });
  }

  loadProducts() {
    this.isLoading = true;

    const params: any = {
      page:  this.currentPage,
      limit: 12,
      sort:  this.sortBy
    };

    if (this.searchQuery)      params['search']    = this.searchQuery;
    if (this.selectedCategory) params['category']  = this.selectedCategory;
    if (this.selectedBrand)    params['brand']     = this.selectedBrand;
    if (this.minPrice != null) params['min_price'] = this.minPrice;
    if (this.maxPrice != null) params['max_price'] = this.maxPrice;
    if (this.selectedCondition) params['condition'] = this.selectedCondition;

    this.http.get<any>(`${this.apiUrl}/products/`, { params }).subscribe({
      next: (res) => {
        this.products    = res.data        || [];
        this.totalResults = res.total      || 0;
        this.totalPages  = res.total_pages || 1;
        this.isLoading   = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.isLoading = false;
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

  loadBrands() {
    this.http.get<any>(`${this.apiUrl}/products/meta/brands`).subscribe({
      next: (res) => {
        this.brands = res.data || [];
        this.cdr.detectChanges();
      }
    });
  }

  onSearchInput() {
    this.searchSubject.next(this.searchQuery);
  }

  applyFilters() {
    this.currentPage = 1;
    this.loadProducts();
    this.isMobileFilterOpen = false;
  }

  clearFilters() {
    this.searchQuery       = '';
    this.selectedCategory  = '';
    this.selectedBrand     = '';
    this.minPrice          = null;
    this.maxPrice          = null;
    this.selectedCondition = '';
    this.sortBy            = 'newest';
    this.currentPage       = 1;
    this.loadProducts();
  }

  onSortChange() {
    this.currentPage = 1;
    this.loadProducts();
  }

  goToPage(page: number) {
    if (page < 1 || page > this.totalPages) return;
    this.currentPage = page;
    this.loadProducts();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  getPages(): number[] {
    const pages: number[] = [];
    const start = Math.max(1, this.currentPage - 2);
    const end   = Math.min(this.totalPages, start + 4);
    for (let i = start; i <= end; i++) pages.push(i);
    return pages;
  }

  getProductImage(product: Product): string {
    if (!product.images || product.images.length === 0) return '';
    const originalUrl = product.images[0];
    
    // If it is an Unsplash image, automatically optimize size and quality
    if (originalUrl.includes('unsplash.com')) {
      return `${originalUrl}?auto=format&fit=crop&w=500&q=80`;
    }
    return originalUrl;
  }

  formatPrice(price: number): string {
    return '৳' + price.toLocaleString('en-BD');
  }

  getConditionBadge(condition: string): string {
    const map: Record<string, string> = {
      'new':       'bg-emerald-400/10 text-emerald-400 border-emerald-400/20',
      'excellent': 'bg-blue-400/10 text-blue-400 border-blue-400/20',
      'good':      'bg-yellow-400/10 text-yellow-400 border-yellow-400/20',
      'fair':      'bg-orange-400/10 text-orange-400 border-orange-400/20',
      'damaged':   'bg-red-400/10 text-red-400 border-red-400/20'
    };
    return map[condition] || 'bg-gray-400/10 text-gray-400';
  }

  // ── Wishlist ───────────────────────────────

  loadWishlist() {
    if (!this.authService.isLoggedIn) return;
    this.http.get<any>(`${this.apiUrl}/wishlist/`).subscribe({
      next: (res) => {
        this.wishlistIds = new Set((res.data || []).map((p: any) => p.id));
        this.cdr.detectChanges();
      }
    });
  }

  isWishlisted(productId: string): boolean {
    return this.wishlistIds.has(productId);
  }

  toggleWishlist(product: Product, event: Event) {
    event.preventDefault();
    event.stopPropagation();

    if (!this.authService.isLoggedIn) {
      this.router.navigate(['/login']);
      return;
    }

    if (this.isWishlisted(product.id)) {
      this.http.delete(`${this.apiUrl}/wishlist/${product.id}`).subscribe({
        next: () => {
          this.wishlistIds.delete(product.id);
          this.cdr.detectChanges();
        }
      });
    } else {
      this.http.post(`${this.apiUrl}/wishlist/`, { product_id: product.id }).subscribe({
        next: () => {
          this.wishlistIds.add(product.id);
          this.cdr.detectChanges();
        }
      });
    }
  }

  get activeFilterCount(): number {
    let count = 0;
    if (this.selectedCategory)   count++;
    if (this.selectedBrand)      count++;
    if (this.minPrice != null)   count++;
    if (this.maxPrice != null)   count++;
    if (this.selectedCondition)  count++;
    return count;
  }
}