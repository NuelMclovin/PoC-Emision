import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { PortalShellComponent } from '../portal-shell/portal-shell';
import { CasoResumen, CasosService, ESTADOS_CERRADOS, estadoClase } from '../../services/casos';

type FiltroHistorial = 'todos' | 'aprobado' | 'rechazado';

@Component({
  selector: 'app-historial',
  standalone: true,
  imports: [CommonModule, PortalShellComponent],
  templateUrl: './historial.html',
  styleUrl: './historial.scss',
})
export class HistorialComponent implements OnInit {
  casos: CasoResumen[] = [];
  cargando = true;
  error = '';
  filtro: FiltroHistorial = 'todos';

  constructor(
    private router: Router,
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
        this.casos = casos.filter((caso) => ESTADOS_CERRADOS.includes(caso.estado));
        this.cargando = false;
      },
      error: () => {
        this.error = 'No se pudo cargar el historial.';
        this.cargando = false;
      },
    });
  }

  get aprobados(): number {
    return this.casos.filter((c) => c.estado === 'Aprobado').length;
  }

  get rechazados(): number {
    return this.casos.filter((c) => c.estado === 'Rechazado').length;
  }

  get casosFiltrados(): CasoResumen[] {
    switch (this.filtro) {
      case 'aprobado':
        return this.casos.filter((c) => c.estado === 'Aprobado');
      case 'rechazado':
        return this.casos.filter((c) => c.estado === 'Rechazado');
      default:
        return this.casos;
    }
  }

  setFiltro(filtro: FiltroHistorial): void {
    this.filtro = filtro;
  }

  verCaso(caso: CasoResumen): void {
    this.router.navigate(['/caso', caso.folio]);
  }

  estadoClase(estado: string): string {
    return estadoClase(estado);
  }
}