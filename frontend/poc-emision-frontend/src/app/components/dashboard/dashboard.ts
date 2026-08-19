import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { PortalShellComponent } from '../portal-shell/portal-shell';
import { AuthService } from '../../services/auth';
import { CasosService, CasoResumen, ESTADOS_CERRADOS, estadoClase } from '../../services/casos';
import { TipoAccion } from '../../services/validacion';

type FiltroDashboard = 'todos' | 'abiertos' | 'nueva' | 'renovacion' | 'observado';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, PortalShellComponent],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss',
})
export class DashboardComponent implements OnInit {
  casos: CasoResumen[] = [];
  cargando = true;
  error = '';
  filtro: FiltroDashboard = 'todos';

  constructor(
    private router: Router,
    private auth: AuthService,
    private casosSvc: CasosService,
  ) {}

  ngOnInit(): void {
    this.cargarCasos();
  }

  cargarCasos(): void {
    this.cargando = true;
    this.error = '';
    this.casosSvc.listarCasos({ creado_por: this.auth.getUsername() }).subscribe({
      next: (casos) => {
        this.casos = casos;
        this.cargando = false;
      },
      error: () => {
        this.error = 'No se pudieron cargar tus expedientes. Intenta de nuevo.';
        this.cargando = false;
      },
    });
  }

  get totalAbiertos(): number {
    return this.casos.filter((caso) => !ESTADOS_CERRADOS.includes(caso.estado)).length;
  }

  get abiertosNueva(): number {
    return this.casos.filter((caso) => !ESTADOS_CERRADOS.includes(caso.estado) && caso.tipo_accion === 'nueva').length;
  }

  get abiertosRenovacion(): number {
    return this.casos.filter(
      (caso) => !ESTADOS_CERRADOS.includes(caso.estado) && caso.tipo_accion === 'renovacion',
    ).length;
  }

  get observados(): number {
    return this.casos.filter((caso) => caso.estado === 'Observado').length;
  }

  get casosFiltrados(): CasoResumen[] {
    switch (this.filtro) {
      case 'abiertos':
        return this.casos.filter((caso) => !ESTADOS_CERRADOS.includes(caso.estado));
      case 'nueva':
        return this.casos.filter((caso) => !ESTADOS_CERRADOS.includes(caso.estado) && caso.tipo_accion === 'nueva');
      case 'renovacion':
        return this.casos.filter(
          (caso) => !ESTADOS_CERRADOS.includes(caso.estado) && caso.tipo_accion === 'renovacion',
        );
      case 'observado':
        return this.casos.filter((caso) => caso.estado === 'Observado');
      default:
        return this.casos;
    }
  }

  setFiltro(filtro: FiltroDashboard): void {
    this.filtro = filtro;
  }

  abrirProceso(tipo: TipoAccion): void {
    this.router.navigate([tipo === 'nueva' ? '/gmm/nueva' : '/gmm/renovacion']);
  }

  verExpediente(caso: CasoResumen): void {
    this.router.navigate(['/expediente', caso.folio]);
  }

  estadoClase(estado: CasoResumen['estado']): string {
    return estadoClase(estado);
  }
}