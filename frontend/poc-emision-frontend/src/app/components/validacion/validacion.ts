import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ValidacionService, ReporteValidacion, TipoAccion } from '../../services/validacion';
import { AuthService } from '../../services/auth';

@Component({
  selector: 'app-validacion',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './validacion.html',
  styleUrl: './validacion.scss',
})
export class ValidacionComponent {
  tabActiva: TipoAccion = 'nueva';

  archivoNueva: File | null = null;
  nombreNueva = '';
  archivoRenovacion: File | null = null;
  nombreRenovacion = '';

  cargando = false;
  error = '';

  constructor(
    private validacionSvc: ValidacionService,
    private auth: AuthService,
    private router: Router,
  ) {}

  get username(): string { return this.auth.getUsername(); }

  setTab(tab: TipoAccion): void {
    this.tabActiva = tab;
    this.error = '';
  }

  onArchivoNueva(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files?.length) {
      this.archivoNueva = input.files[0];
      this.nombreNueva = input.files[0].name;
      this.error = '';
    }
  }

  onArchivoRenovacion(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files?.length) {
      this.archivoRenovacion = input.files[0];
      this.nombreRenovacion = input.files[0].name;
      this.error = '';
    }
  }

  get archivoActivo(): File | null {
    return this.tabActiva === 'nueva' ? this.archivoNueva : this.archivoRenovacion;
  }

  validar(): void {
    if (!this.archivoActivo) return;
    this.cargando = true;
    this.error = '';

    this.validacionSvc.validarMacro(this.archivoActivo, this.tabActiva, 'GMM').subscribe({
      next: (reporte: ReporteValidacion) => {
        this.cargando = false;
        sessionStorage.setItem('ultimo_reporte', JSON.stringify(reporte));
        this.router.navigate(['/reporte']);
      },
      error: (err: { error?: { detail?: string } }) => {
        this.cargando = false;
        this.error = err?.error?.detail ?? 'Error al procesar la macro. Verifica el archivo e intenta de nuevo.';
      },
    });
  }

  logout(): void {
    this.auth.logout();
    this.router.navigate(['/login']);
  }
}
