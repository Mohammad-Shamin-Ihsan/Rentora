import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/services/auth.service';

interface Category {
  id:   string;
  name: string;
}

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

interface ProductForm {
  title:                 string;
  brand:                 string;
  description:           string;
  category_id:           string;
  rental_price_per_day:  number | null;
  security_deposit:      number | null;
  condition:             string;
  image_url:             string;
}

const EMPTY_PRODUCT_FORM: ProductForm = {
  title: '', brand: '', description: '', category_id: '',
  rental_price_per_day: null, security_deposit: null,
  condition: 'good', image_url: ''
};

@Component({
  selector: 'app-my-listings',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './my-listings.html',
  styleUrls: ['./my-listings.css']
})
export class MyListings implements OnInit {

  private apiUrl = environment.apiUrl;

  products: Product[] = [];
  isLoading = true;
  updatingId: string | null = null;
  errorMessage = '';

  categories: Category[] = [];

  showEditForm = false;
  editingProductId: string | null = null;
  form: ProductForm = { ...EMPTY_PRODUCT_FORM };
  isSubmitting = false;
  formError = '';

  deletingId: string | null = null;

  constructor(
    private http:        HttpClient,
    private cdr:         ChangeDetectorRef,
    public  authService: AuthService
  ) {}

  ngOnInit() {
    if (this.isSeller) {
      this.loadProducts();
      this.loadCategories();
    } else {
      this.isLoading = false;
    }
  }

  get isSeller(): boolean {
    return this.authService.currentUser?.role === 'seller';
  }

  loadProducts() {
    this.isLoading = true;
    this.http.get<any>(`${this.apiUrl}/sellers/products`).subscribe({
      next: (res) => {
        this.products = res.data || [];
        this.isLoading = false;
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

  setStatus(product: Product, status: 'available' | 'maintenance') {
    if (product.status === status || this.updatingId) return;

    this.errorMessage = '';
    this.updatingId = product.id;
    this.cdr.detectChanges();

    this.http.patch<any>(`${this.apiUrl}/sellers/products/${product.id}/status`, { status }).subscribe({
      next: () => {
        product.status = status;
        this.updatingId = null;
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.errorMessage = err.error?.detail || 'Failed to update status.';
        this.updatingId = null;
        this.cdr.detectChanges();
      }
    });
  }

  openEditForm(product: Product) {
    this.editingProductId = product.id;
    this.form = {
      title:                product.title,
      brand:                product.brand || '',
      description:          product.description || '',
      category_id:          product.category_id || '',
      rental_price_per_day: Number(product.rental_price_per_day),
      security_deposit:     Number(product.security_deposit),
      condition:            product.condition,
      image_url:            (product.images && product.images.length > 0) ? product.images[0] : ''
    };
    this.formError = '';
    this.showEditForm = true;
    this.cdr.detectChanges();
  }

  closeEditForm() {
    this.showEditForm = false;
    this.editingProductId = null;
    this.cdr.detectChanges();
  }

  submitEditForm() {
    this.formError = '';

    if (!this.form.title.trim()) {
      this.formError = 'Title is required.';
      return;
    }
    if (!this.form.category_id) {
      this.formError = 'Please choose a category.';
      return;
    }
    if (!this.form.rental_price_per_day || this.form.rental_price_per_day <= 0) {
      this.formError = 'Rental price must be greater than zero.';
      return;
    }
    if (this.form.security_deposit === null || this.form.security_deposit < 0) {
      this.formError = 'Security deposit cannot be negative.';
      return;
    }

    this.isSubmitting = true;
    this.cdr.detectChanges();

    const images = this.form.image_url.trim() ? [this.form.image_url.trim()] : [];
    const body = {
      title:                 this.form.title.trim(),
      brand:                 this.form.brand.trim() || null,
      description:           this.form.description.trim() || null,
      category_id:           this.form.category_id,
      rental_price_per_day:  this.form.rental_price_per_day,
      security_deposit:      this.form.security_deposit,
      condition:             this.form.condition,
      images,
      technical_specifications: {}
    };

    this.http.patch<any>(`${this.apiUrl}/sellers/products/${this.editingProductId}`, body).subscribe({
      next: () => {
        this.isSubmitting = false;
        this.showEditForm = false;
        this.editingProductId = null;
        this.loadProducts();
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.formError = err.error?.detail || 'Failed to save the changes.';
        this.isSubmitting = false;
        this.cdr.detectChanges();
      }
    });
  }

  deleteProduct(product: Product) {
    if (!confirm(`Delete "${product.title}"? This can't be undone.`)) return;

    this.errorMessage = '';
    this.deletingId = product.id;
    this.cdr.detectChanges();

    this.http.delete<any>(`${this.apiUrl}/sellers/products/${product.id}`).subscribe({
      next: () => {
        this.deletingId = null;
        this.loadProducts();
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.errorMessage = err.error?.detail || 'Failed to delete the product.';
        this.deletingId = null;
        this.cdr.detectChanges();
      }
    });
  }

  formatPrice(price: number): string {
    return '৳' + Number(price).toLocaleString('en-BD');
  }
}
