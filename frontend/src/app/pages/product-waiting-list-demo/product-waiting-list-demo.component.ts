import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { WaitingListComponent } from '../../components/waiting-list/waiting-list.component';

@Component({
  selector: 'app-product-waiting-list-demo',
  standalone: true,
  imports: [CommonModule, WaitingListComponent],
  templateUrl: './product-waiting-list-demo.component.html',
  styleUrls: ['./product-waiting-list-demo.component.css'],
})
export class ProductWaitingListDemoComponent {
  /** Product ID 1 = "DJI Mavic 3 Cine" seeded by db_init.py */
  productId = 1;

  /** Customer currently viewing the page (switchable via demo UI) */
  currentUserId = 1;

  /** Admin user ID for the admin-panel column */
  adminUserId = 4; // "Admin User" from seed data

  /** User IDs available in the demo switcher */
  testUserIds = [1, 2, 3];

  /** API endpoints displayed in the reference table */
  apiEndpoints = [
    {
      method: 'POST',
      path: '/products/{id}/waiting-list',
      desc: 'Join the waiting list',
    },
    {
      method: 'DELETE',
      path: '/products/{id}/waiting-list',
      desc: 'Leave the waiting list',
    },
    {
      method: 'GET',
      path: '/products/{id}/waiting-list/status',
      desc: 'Check own status & queue position',
    },
    {
      method: 'GET',
      path: '/products/{id}/waiting-list',
      desc: 'List full queue (admin)',
    },
    {
      method: 'POST',
      path: '/products/{id}/waiting-list/notify',
      desc: 'Trigger availability notifications',
    },
  ];
}
