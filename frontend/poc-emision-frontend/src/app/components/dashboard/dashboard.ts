import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { PortalShellComponent } from '../portal-shell/portal-shell';
import { EXPEDIENTES_MOCK, Expediente, estadoClase } from '../shared/portal-data';
import { TipoAccion } from '../../services/validacion';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, PortalShellComponent],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss',
})
export class DashboardComponent {
  readonly expedientes: Expediente[] = EXPEDIENTES_MOCK;

  constructor(private router: Router) {}

  get totalAbiertos(): number {
    return this.expedientes.filter((expediente) => expediente.estado !== 'Completado').length;
  }

  get abiertosNueva(): number {
    return this.expedientes.filter((expediente) => expediente.estado !== 'Completado' && expediente.tipo === 'GMM Nueva').length;
  }

  get abiertosRenovacion(): number {
    return this.expedientes.filter((expediente) => expediente.estado !== 'Completado' && expediente.tipo === 'GMM Renovacion').length;
  }

  get observados(): number {
    return this.expedientes.filter((expediente) => expediente.estado === 'Observado').length;
  }

  abrirProceso(tipo: TipoAccion): void {
    this.router.navigate([tipo === 'nueva' ? '/gmm/nueva' : '/gmm/renovacion']);
  }

  verExpediente(expediente: Expediente): void {
    this.router.navigate([expediente.tipo === 'GMM Nueva' ? '/gmm/nueva' : '/gmm/renovacion']);
  }

  estadoClase(estado: Expediente['estado']): string {
    return estadoClase(estado);
  }
}