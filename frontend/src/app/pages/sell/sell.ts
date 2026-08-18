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
  selector: 'app-sell',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './sell.html',
  styleUrls: ['./sell.css']
})
export class Sell implements OnInit {

  private apiUrl = environment.apiUrl;

  isStaffAccount = false;
  isBecomingSeller = false;
  becomeSellerError = '';

  categories: Category[] = [];

  form: ProductForm = { ...EMPTY_PRODUCT_FORM };
  isSubmitting = false;
  formError = '';
  successMessage = '';

  constructor(
    private http:        HttpClient,
    private cdr:         ChangeDetectorRef,
    public  authService: AuthService
  ) {}

  ngOnInit() {
    const role = this.authService.currentUser?.role;
    if (role === 'admin' || role === 'cargo_manager' || role === 'warehouse_staff') {
      this.isStaffAccount = true;
      return;
    }

    if (role === 'seller') {
      this.loadCategories();
    }
  }

  get isSeller(): boolean {
    return this.authService.currentUser?.role === 'seller';
  }

  becomeSeller() {
    this.becomeSellerError = '';
    this.isBecomingSeller = true;
    this.cdr.detectChanges();

    this.http.post<any>(`${this.apiUrl}/sellers/become`, {}).subscribe({
      next: (res) => {
        this.authService.updateCachedUser(res.user);
        this.isBecomingSeller = false;
        this.loadCategories();
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.becomeSellerError = err.error?.detail || 'Failed to become a seller.';
        this.isBecomingSeller = false;
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

  submitForm() {
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

    this.http.post<any>(`${this.apiUrl}/sellers/products`, body).subscribe({
      next: () => {
        this.isSubmitting = false;
        this.successMessage = `"${this.form.title.trim()}" was listed successfully.`;
        this.form = { ...EMPTY_PRODUCT_FORM };
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.formError = err.error?.detail || 'Failed to save the listing.';
        this.isSubmitting = false;
        this.cdr.detectChanges();
      }
    });
  }
}
