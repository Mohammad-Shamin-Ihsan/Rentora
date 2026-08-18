import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/home/home').then(m => m.Home)
  },
  {
    path: 'login',
    loadComponent: () =>
      import('./pages/login/login').then(m => m.Login)
  },
  {
    path: 'register',
    loadComponent: () =>
      import('./pages/register/register').then(m => m.Register)
  },
  {
    path: 'browse',
    loadComponent: () =>
      import('./pages/browse/browse').then(m => m.Browse)
  },
  {
    path: 'products/:id',
    loadComponent: () =>
      import('./pages/product-detail/product-detail')
        .then(m => m.ProductDetail)
  },
  {
    path: 'profile',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./pages/profile/profile').then(m => m.Profile)
  },
  {
    path: 'rentals',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./pages/rentals/rentals').then(m => m.Rentals)
  },
  {
    path: 'import',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./pages/import/import').then(m => m.Import)
  },
  {
    path: 'admin',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./pages/admin/dashboard/dashboard')
        .then(m => m.Dashboard )
  },
  {
    path: 'warehouse',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./pages/warehouse/inspection/inspection')
        .then(m => m.Inspection)
  },
  {
    path: '**',
    redirectTo: ''
  }
];