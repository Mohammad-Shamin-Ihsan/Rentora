import {
  Component,
  Input,
  OnChanges,
  OnInit,
  SimpleChanges,
} from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { WaitingListService } from '../../services/waiting-list.service';
import { WaitingListEntry, WaitingListStatus } from '../../models/waiting-list.model';

/**
 * WaitingListComponent — Module 2 / Part 4: Waiting List Management.
 *
 * Usage:
 *   <app-waiting-list
 *     [productId]="product.id"
 *     [currentUserId]="loggedInUserId"
 *     [showAdminPanel]="isAdmin">
 *   </app-waiting-list>
 *
 * - When the product is unavailable, shows a "Notify Me When Available" button.
 * - When the user is already on the list, shows their queue position + a leave button.
 * - showAdminPanel=true reveals the full queue and a "Send Notifications" button.
 */
@Component({
  selector: 'app-waiting-list',
  standalone: true,
  imports: [CommonModule, DatePipe],
  templateUrl: './waiting-list.component.html',
  styleUrls: ['./waiting-list.component.css'],
})
export class WaitingListComponent implements OnInit, OnChanges {
  @Input({ required: true }) productId!: number;
  @Input({ required: true }) currentUserId!: number;
  /** Set true to show the admin queue panel (admins/staff only). */
  @Input() showAdminPanel = false;

  status: WaitingListStatus | null = null;
  queueEntries: WaitingListEntry[] = [];
  loading = true;
  actionLoading = false;
  errorMessage: string | null = null;
  successMessage: string | null = null;
  adminExpanded = false;

  constructor(private wlService: WaitingListService) {}

  ngOnInit(): void {
    this.load();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['productId'] || changes['currentUserId']) {
      this.load();
    }
  }

  load(): void {
    if (!this.productId || !this.currentUserId) return;
    this.loading = true;
    this.errorMessage = null;

    this.wlService.getStatus(this.productId, this.currentUserId).subscribe({
      next: (s) => {
        this.status = s;
        this.loading = false;
        if (this.showAdminPanel) this.loadQueue();
      },
      error: (err) => {
        // If the product is available, the backend returns 400 with a clear
        // message — surface that so we know not to show the waiting list UI.
        this.errorMessage =
          err?.error?.detail ?? "Couldn't load waiting list status.";
        this.loading = false;
      },
    });
  }

  loadQueue(): void {
    this.wlService.listAll(this.productId).subscribe({
      next: (entries) => (this.queueEntries = entries),
      error: () => {}, // silently skip queue list errors
    });
  }

  join(): void {
    this.actionLoading = true;
    this.errorMessage = null;
    this.successMessage = null;

    this.wlService.join(this.productId, this.currentUserId).subscribe({
      next: (entry) => {
        this.actionLoading = false;
        this.showSuccess(
          `You've joined the waiting list! You are #${entry.queue_position ?? '?'} in queue.`
        );
        this.load();
      },
      error: (err) => {
        this.actionLoading = false;
        this.errorMessage = err?.error?.detail ?? 'Failed to join the waiting list.';
      },
    });
  }

  leave(): void {
    this.actionLoading = true;
    this.errorMessage = null;
    this.successMessage = null;

    this.wlService.cancel(this.productId, this.currentUserId).subscribe({
      next: () => {
        this.actionLoading = false;
        this.showSuccess("You've been removed from the waiting list.");
        this.load();
      },
      error: (err) => {
        this.actionLoading = false;
        this.errorMessage = err?.error?.detail ?? 'Failed to leave the waiting list.';
      },
    });
  }

  notifyAll(): void {
    this.actionLoading = true;

    this.wlService.notifyAll(this.productId).subscribe({
      next: (res) => {
        this.actionLoading = false;
        this.showSuccess(res.message);
        this.loadQueue();
        this.load();
      },
      error: (err) => {
        this.actionLoading = false;
        this.errorMessage = err?.error?.detail ?? 'Failed to send notifications.';
      },
    });
  }

  private showSuccess(msg: string): void {
    this.successMessage = msg;
    setTimeout(() => (this.successMessage = null), 5000);
  }
}
