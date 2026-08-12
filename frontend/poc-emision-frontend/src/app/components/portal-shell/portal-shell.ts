import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth';
import { SeccionPortal } from '../shared/portal-data';

@Component({
  selector: 'app-portal-shell',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './portal-shell.html',
  styleUrl: './portal-shell.scss',
})
export class PortalShellComponent {
  @Input({ required: true }) titulo = '';
  @Input() subtitulo = '';
  @Input({ required: true }) seccionActiva: SeccionPortal = 'dashboard';
  @Input() totalAbiertos = 0;

  menuColapsado = false;

  constructor(
    private auth: AuthService,
    private router: Router,
  ) {}

  get username(): string {
    return this.auth.getUsername();
  }

  toggleMenu(): void {
    this.menuColapsado = !this.menuColapsado;
  }

  irASeccion(vista: SeccionPortal): void {
    const destino = vista === 'dashboard'
      ? '/dashboard'
      : vista === 'nueva'
        ? '/gmm/nueva'
        : '/gmm/renovacion';

    this.router.navigate([destino]);
  }

  logout(): void {
    this.auth.logout();
    this.router.navigate(['/login']);
  }
}