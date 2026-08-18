import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

// Admins manage the platform from /admin — they don't browse, import, or rent.
export const notAdminGuard: CanActivateFn = () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (authService.currentUser?.role === 'admin') {
    router.navigate(['/admin']);
    return false;
  }

  return true;
};
