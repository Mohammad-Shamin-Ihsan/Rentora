import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/services/auth.service';

interface ProfileData {
  id:           string;
  full_name:    string;
  email:        string;
  role:         string;
  phone_number: string | null;
  created_at:   string;
}

interface WishlistItem {
  id:                    string;
  title:                 string;
  images:                string[];
  rental_price_per_day:  number;
  status:                string;
}

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './profile.html',
  styleUrls: ['./profile.css']
})
export class Profile implements OnInit {

  private apiUrl = environment.apiUrl;

  profile:     ProfileData | null = null;
  isLoading    = true;
  isSaving     = false;
  errorMessage = '';
  successMessage = '';

  fullName    = '';
  phoneNumber = '';

  wishlist:          WishlistItem[] = [];
  isLoadingWishlist   = true;

  constructor(
    private http: HttpClient,
    public  authService: AuthService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.loadProfile();
    this.loadWishlist();
  }

  loadWishlist() {
    this.isLoadingWishlist = true;
    this.http.get<any>(`${this.apiUrl}/wishlist/`).subscribe({
      next: (res) => {
        this.wishlist          = res.data || [];
        this.isLoadingWishlist = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.isLoadingWishlist = false;
        this.cdr.detectChanges();
      }
    });
  }

  removeFromWishlist(item: WishlistItem) {
    this.http.delete(`${this.apiUrl}/wishlist/${item.id}`).subscribe({
      next: () => {
        this.wishlist = this.wishlist.filter(w => w.id !== item.id);
        this.cdr.detectChanges();
      }
    });
  }

  getWishlistImage(item: WishlistItem): string {
    if (!item.images || item.images.length === 0) return '';
    const url = item.images[0];
    return url.includes('unsplash.com') ? `${url}?auto=format&fit=crop&w=200&q=80` : url;
  }

  formatPrice(price: number): string {
    return '৳' + Number(price).toLocaleString('en-BD');
  }

  loadProfile() {
    this.isLoading = true;
    this.http.get<ProfileData>(`${this.apiUrl}/auth/me`).subscribe({
      next: (profile) => {
        this.profile     = profile;
        this.fullName    = profile.full_name;
        this.phoneNumber = profile.phone_number || '';
        this.isLoading   = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.errorMessage = 'Could not load your profile.';
        this.isLoading     = false;
        this.cdr.detectChanges();
      }
    });
  }

  saveProfile() {
    this.isSaving      = true;
    this.errorMessage  = '';
    this.successMessage = '';

    this.http.patch<ProfileData>(`${this.apiUrl}/auth/me`, {
      full_name:    this.fullName,
      phone_number: this.phoneNumber
    }).subscribe({
      next: (profile) => {
        this.profile      = profile;
        this.isSaving      = false;
        this.successMessage = 'Profile updated successfully.';

        // Keep navbar / cached user in sync
        const current = this.authService.currentUser;
        if (current) {
          this.authService.updateCachedUser({ ...current, full_name: profile.full_name });
        }
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.isSaving     = false;
        this.errorMessage = err.error?.detail || 'Failed to update profile.';
        this.cdr.detectChanges();
      }
    });
  }

  formatDate(dateStr: string): string {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'long', day: 'numeric', year: 'numeric'
    });
  }
}
