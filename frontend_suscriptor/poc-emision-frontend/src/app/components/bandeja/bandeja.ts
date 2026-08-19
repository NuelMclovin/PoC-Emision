import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { PortalShellComponent } from '../portal-shell/portal-shell';
import { AuthService } from '../../services/auth';
import { CasoResumen, CasosService, ESTADOS_CERRADOS, estadoClase } from '../../services/casos';

type Tab = 'todos' | 'pendiente' | 'en-revision' | 'observado' | 'mios';

@Component({
  selector: 'app-bandeja',
  standalone: true,
  imports: [CommonModule, PortalShellComponent],
  templateUrl: './bandeja.html',
  styleUrl: './bandeja.scss',
})
export class BandejaComponent implements OnInit {
  casos: CasoResumen[] = [];
  cargando = true;
  error = '';
  tab: Tab = 'todos';

  constructor(
    private router: Router,
    private auth: AuthService,
    private casosSvc: CasosService,
  ) {}

  ngOnInit(): void {
    this.cargar();
  }

  cargar(): void {
    this.cargando = true;
    this.error = '';
    this.casosSvc.listarCasos({}).subscribe({
      next: (casos) => {
        this.casos = casos.filter((caso) => !ESTADOS_CERRADOS.includes(caso.estado));
        this.cargando = false;
      },
      error: () => {
        this.error = 'No se pudo cargar la bandeja de revisión.';
        this.cargando = false;
      },
    });
  }

  get totalAbiertos(): number {
    return this.casos.length;
  }

  get pendientes(): CasoResumen[] {
    return this.casos.filter((c) => c.estado === 'Pendiente');
  }

  get enRevision(): CasoResumen[] {
    return this.casos.filter((c) => c.estado === 'En revisión');
  }

  get observados(): CasoResumen[] {
    return this.casos.filter((c) => c.estado === 'Observado');
  }

  get misAsignados(): CasoResumen[] {
    const username = this.auth.getUsername();
    return this.casos.filter((c) => c.asignado_a === username);
  }

  get casosFiltrados(): CasoResumen[] {
    switch (this.tab) {
      case 'pendiente':
        return this.pendientes;
      case 'en-revision':
        return this.enRevision;
      case 'observado':
        return this.observados;
      case 'mios':
        return this.misAsignados;
      default:
        return this.casos;
    }
  }

  setTab(tab: Tab): void {
    this.tab = tab;
  }

  verCaso(caso: CasoResumen): void {
    this.router.navigate(['/caso', caso.folio]);
  }

  tomarCaso(caso: CasoResumen, event: Event): void {
    event.stopPropagation();
    this.casosSvc.actualizarCaso(caso.folio, { estado: 'En revisión' }).subscribe({
      next: () => this.cargar(),
      error: () => {
        this.error = `No se pudo tomar el caso ${caso.folio}.`;
      },
    });
  }

  estadoClase(estado: string): string {
    return estadoClase(estado);
  }
}