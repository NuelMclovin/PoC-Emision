import { HttpInterceptorFn } from '@angular/common/http';

/**
 * Interceptor funcional que agrega el Bearer token de sesión
 * a todas las peticiones hacia la API del backend.
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const token = localStorage.getItem('poc_token');

  if (token) {
    const authReq = req.clone({
      setHeaders: { Authorization: `Bearer ${token}` },
    });
    return next(authReq);
  }

  return next(req);
};
