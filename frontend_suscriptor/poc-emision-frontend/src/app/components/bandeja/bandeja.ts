import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
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
    private cdr: ChangeDetectorRef,
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
        // Esta actualización viene de un callback HTTP asíncrono, no de un
        // evento de plantilla (click, etc.). En esta versión de Angular eso
        // ya no basta para que la vista se repinte sola: hay que marcar la
        // vista explícitamente para que el próximo ciclo de CD la recoja.
        this.cdr.markForCheck();
      },
      error: () => {
        this.error = 'No se pudo cargar la bandeja de revisión.';
        this.cargando = false;
        this.cdr.markForCheck();
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
        this.cdr.markForCheck();
      },
    });
  }

  estadoClase(estado: string): string {
    return estadoClase(estado);
  }
}