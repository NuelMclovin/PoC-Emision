import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth';

/**
 * Este frontend es el portal de suscripción interna. Solo usuarios con
 * rol 'suscriptor' pueden navegar aquí; un bróker debe usar el portal de
 * conducto (frontend/poc-emision-frontend).
 */
export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (auth.isLoggedIn() && auth.getRol() === 'suscriptor') {
    return true;
  }

  if (auth.isLoggedIn()) {
    auth.logout();
  }

  return router.createUrlTree(['/login']);
};