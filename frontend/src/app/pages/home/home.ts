import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';

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
}

interface Category {
  id: string;
  name: string;
  description: string;
}

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './home.html',
  styleUrls: ['./home.css']
})
export class Home implements OnInit {

  private apiUrl = environment.apiUrl;

  trendingProducts: Product[] = [];
  categories: Category[] = [];
  isLoadingProducts = true;
  isLoadingCategories = true;

  // Category nav items matching the design
  categoryNav = [
    { label: 'Home',     path: '/' },
    { label: 'Wedding',  path: '/browse?category=Wedding' },
    { label: 'Drones',   path: '/browse?category=Drones' },
    { label: 'Tools',    path: '/browse?category=Tools' },
    { label: 'Camping',  path: '/browse?category=Camping' },
    { label: 'Audio',    path: '/browse?category=Audio' },
    { label: 'Import',   path: '/import' }
  ];

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.loadTrendingProducts();
    this.loadCategories();
  }

  loadTrendingProducts() {
    this.http.get<any>(`${this.apiUrl}/products/?limit=4`).subscribe({
      next: (res) => {
        this.trendingProducts = res.data || [];
        this.isLoadingProducts = false;
      },
      error: () => {
        this.isLoadingProducts = false;
      }
    });
  }

  loadCategories() {
    this.http.get<any>(`${this.apiUrl}/products/categories`).subscribe({
      next: (res) => {
        this.categories = res.data || [];
        this.isLoadingCategories = false;
      },
      error: () => {
        this.isLoadingCategories = false;
      }
    });
  }

  getProductImage(product: Product): string {
    if (!product.images || product.images.length === 0) {
      return 'assets/images/placeholder.jpg';
    }
    const originalUrl = product.images[0];
    if (originalUrl.includes('unsplash.com')) {
      return `${originalUrl}?auto=format&fit=crop&w=500&q=80`;
    }
    return originalUrl;
  }

  formatPrice(price: number): string {
    return '৳' + price.toLocaleString('en-BD');
  }

  getStars(rating: number): number[] {
    return Array(5).fill(0).map((_, i) => i + 1);
  }

  getConditionColor(condition: string): string {
    const map: Record<string, string> = {
      'new':       'text-emerald-400 bg-emerald-400/10',
      'excellent': 'text-blue-400 bg-blue-400/10',
      'good':      'text-yellow-400 bg-yellow-400/10',
      'fair':      'text-orange-400 bg-orange-400/10',
      'damaged':   'text-red-400 bg-red-400/10'
    };
    return map[condition] || 'text-gray-400 bg-gray-400/10';
  }
}