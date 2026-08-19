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
        path: 'dashboard',
        loadComponent: () =>
          import('./components/dashboard/dashboard').then(m => m.DashboardComponent),
      },
      {
        path: 'gmm/nueva',
        loadComponent: () =>
          import('./components/nueva-gmm/nueva-gmm').then(m => m.NuevaGmmComponent),
      },
      {
        path: 'gmm/renovacion',
        loadComponent: () =>
          import('./components/renovacion-gmm/renovacion-gmm').then(m => m.RenovacionGmmComponent),
      },
      {
        path: 'reporte',
        loadComponent: () =>
          import('./components/reporte/reporte').then(m => m.ReporteComponent),
      },
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
      { path: 'validacion', redirectTo: 'dashboard', pathMatch: 'full' },
    ],
  },
  { path: '**', redirectTo: 'login' },
];
