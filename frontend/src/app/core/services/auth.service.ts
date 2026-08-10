import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, tap } from 'rxjs';
import { Router } from '@angular/router';
import { environment } from '../../../environments/environment';

export interface User {
  id: string;
  full_name: string;
  email: string;
  role: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {

  private apiUrl = environment.apiUrl;
  private currentUserSubject = new BehaviorSubject<User | null>(null);
  currentUser$ = this.currentUserSubject.asObservable();

  constructor(private http: HttpClient, private router: Router) {
    // Restore session from localStorage on page refresh
    const saved = localStorage.getItem('rentora_user');
    if (saved) {
      this.currentUserSubject.next(JSON.parse(saved));
    }
  }

  register(data: {
    full_name: string;
    email: string;
    password: string;
    role: string;
  }) {
    return this.http
      .post<any>(`${this.apiUrl}/auth/register`, data)
      .pipe(
        tap(response => {
          // Save user to localStorage after registration
          localStorage.setItem(
            'rentora_user',
            JSON.stringify(response.user)
          );
          this.currentUserSubject.next(response.user);
        })
      );
  }

  login(email: string, password: string) {
    return this.http
      .post<any>(`${this.apiUrl}/auth/login`, { email, password })
      .pipe(
        tap(response => {
          // Save user to localStorage after login
          localStorage.setItem(
            'rentora_user',
            JSON.stringify(response.user)
          );
          this.currentUserSubject.next(response.user);
        })
      );
  }

  logout() {
    localStorage.removeItem('rentora_user');
    this.currentUserSubject.next(null);
    this.router.navigate(['/']);
  }

  get currentUser(): User | null {
    return this.currentUserSubject.value;
  }

  get isLoggedIn(): boolean {
    return !!this.currentUserSubject.value;
  }

  get userRole(): string {
    return this.currentUserSubject.value?.role || 'customer';
  }

  // Keep this so interceptor doesn't break (returns null now)
  getToken(): string | null {
    return null;
  }
}