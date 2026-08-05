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
        path: 'validacion',
        loadComponent: () =>
          import('./components/validacion/validacion').then(m => m.ValidacionComponent),
      },
      {
        path: 'reporte',
        loadComponent: () =>
          import('./components/reporte/reporte').then(m => m.ReporteComponent),
      },
      { path: '', redirectTo: 'validacion', pathMatch: 'full' },
    ],
  },
  { path: '**', redirectTo: 'login' },
];
