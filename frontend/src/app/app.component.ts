import { Component } from '@angular/core';
import { ProductWaitingListDemoComponent } from './pages/product-waiting-list-demo/product-waiting-list-demo.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [ProductWaitingListDemoComponent],
  template: '<app-product-waiting-list-demo></app-product-waiting-list-demo>',
})
export class AppComponent {}
