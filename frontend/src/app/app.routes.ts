import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { notAdminGuard } from './core/guards/not-admin.guard';

export const routes: Routes = [
  {
    path: '',
    canActivate: [notAdminGuard],
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
    canActivate: [notAdminGuard],
    loadComponent: () =>
      import('./pages/browse/browse').then(m => m.Browse)
  },
  {
    path: 'products/:id',
    canActivate: [notAdminGuard],
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
    canActivate: [authGuard, notAdminGuard],
    loadComponent: () =>
      import('./pages/rentals/rentals').then(m => m.Rentals)
  },
  {
    path: 'import',
    canActivate: [authGuard, notAdminGuard],
    loadComponent: () =>
      import('./pages/import/import').then(m => m.Import)
  },
  {
    path: 'sell',
    canActivate: [authGuard, notAdminGuard],
    loadComponent: () =>
      import('./pages/sell/sell').then(m => m.Sell)
  },
  {
    path: 'my-listings',
    canActivate: [authGuard, notAdminGuard],
    loadComponent: () =>
      import('./pages/my-listings/my-listings').then(m => m.MyListings)
  },
  {
    path: 'admin',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./pages/admin/dashboard/dashboard')
        .then(m => m.Dashboard )
  },
  {
    path: 'cargo',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./pages/cargo/cargo').then(m => m.Cargo)
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