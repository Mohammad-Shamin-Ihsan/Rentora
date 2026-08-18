import { ChangeDetectorRef, Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { Subscription, interval } from 'rxjs';
import { AuthService } from '../../../core/services/auth.service';
import { environment } from '../../../../environments/environment';

interface NotificationItem {
  id:         string;
  title:      string;
  message:    string;
  is_read:    boolean;
  created_at: string;
}

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './navbar.html',
  styleUrls: ['./navbar.css']
})
export class NavbarComponent implements OnInit, OnDestroy {

  private apiUrl = environment.apiUrl;

  notifications:  NotificationItem[] = [];
  unreadCount     = 0;
  isDropdownOpen  = false;

  private authSub?: Subscription;
  private pollSub?: Subscription;

  constructor(
    public  authService: AuthService,
    private http:        HttpClient,
    private cdr:         ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.authSub = this.authService.currentUser$.subscribe(user => {
      if (user) {
        this.loadNotifications();
      } else {
        this.notifications = [];
        this.unreadCount   = 0;
      }
      this.cdr.detectChanges();
    });

    // Light polling so a waitlist notification (or similar) shows up
    // without the user needing to refresh the page.
    this.pollSub = interval(30000).subscribe(() => {
      if (this.authService.isLoggedIn) this.loadNotifications();
    });
  }

  ngOnDestroy() {
    this.authSub?.unsubscribe();
    this.pollSub?.unsubscribe();
  }

  loadNotifications() {
    this.http.get<any>(`${this.apiUrl}/notifications/`).subscribe({
      next: (res) => {
        this.notifications = res.data || [];
        this.unreadCount   = res.unread_count || 0;
        this.cdr.detectChanges();
      }
    });
  }

  toggleDropdown() {
    this.isDropdownOpen = !this.isDropdownOpen;
    if (this.isDropdownOpen) this.loadNotifications();
    this.cdr.detectChanges();
  }

  closeDropdown() {
    this.isDropdownOpen = false;
    this.cdr.detectChanges();
  }

  markRead(n: NotificationItem) {
    if (n.is_read) return;
    this.http.patch(`${this.apiUrl}/notifications/${n.id}/read`, {}).subscribe({
      next: () => {
        n.is_read      = true;
        this.unreadCount = Math.max(0, this.unreadCount - 1);
        this.cdr.detectChanges();
      }
    });
  }

  markAllRead() {
    this.http.patch(`${this.apiUrl}/notifications/read-all`, {}).subscribe({
      next: () => {
        this.notifications.forEach(n => n.is_read = true);
        this.unreadCount = 0;
        this.cdr.detectChanges();
      }
    });
  }

  formatTime(dateStr: string): string {
    const diffMs = Date.now() - new Date(dateStr).getTime();
    const mins   = Math.floor(diffMs / 60000);
    if (mins < 1)  return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24)  return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  }
}
