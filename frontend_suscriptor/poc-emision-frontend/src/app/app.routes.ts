import { Routes } from '@angular/router';
import { authGuard } from './guards/auth-guard';
import { LoginComponent } from './components/login/login';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  {
    path: '',
    canActivate: [authGuard],
    children: [
      {
        path: 'bandeja',
        loadComponent: () =>
          import('./components/bandeja/bandeja').then(m => m.BandejaComponent),
      },
      {
        path: 'historial',
        loadComponent: () =>
          import('./components/historial/historial').then(m => m.HistorialComponent),
      },
      {
        path: 'caso/:folio',
        loadComponent: () =>
          import('./components/caso-detalle/caso-detalle').then(m => m.CasoDetalleComponent),
      },
      { path: '', redirectTo: 'bandeja', pathMatch: 'full' },
    ],
  },
  { path: '**', redirectTo: 'login' },
];