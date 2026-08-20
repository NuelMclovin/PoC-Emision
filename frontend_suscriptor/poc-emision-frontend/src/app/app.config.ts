import { ApplicationConfig, provideBrowserGlobalErrorListeners, provideZoneChangeDetection } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient, withInterceptors, withXhr } from '@angular/common/http';

import { routes } from './app.routes';
import { authInterceptor } from './interceptors/auth.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    // Habilita zone.js (con coalescing de eventos) para que la UI se refresque
    // automaticamente al recibir respuestas HTTP/websocket, sin depender de
    // que el usuario dispare un evento manual (click, etc.).
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(routes),
    // IMPORTANTE: desde Angular 20+, provideHttpClient() usa `fetch()` como
    // backend por defecto en vez de XMLHttpRequest. zone.js NO parchea
    // `fetch` (se eliminó de sus patches por defecto hace varias versiones),
    // así que las peticiones HTTP nunca marcaban la zona como "inestable" y
    // Angular jamás disparaba detección de cambios automática al recibir la
    // respuesta — los datos llegaban, pero la vista sólo se repintaba cuando
    // algún otro evento (un clic) disparaba CD por su cuenta. `withXhr()`
    // fuerza de vuelta el backend XMLHttpRequest clásico, que sí está
    // parcheado por zone.js, para que la UI se actualice sola.
    provideHttpClient(withInterceptors([authInterceptor]), withXhr()),
  ]
};