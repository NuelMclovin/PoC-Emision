import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth';

/**
 * Este frontend es el portal de cara al bróker (conducto). Solo usuarios con
 * rol 'broker' pueden navegar aquí; un usuario suscriptor debe usar el
 * portal de suscripción interno (frontend_suscriptor).
 */
export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (auth.isLoggedIn() && auth.getRol() === 'broker') {
    return true;
  }

  if (auth.isLoggedIn()) {
    auth.logout();
  }

  return router.createUrlTree(['/login']);
};