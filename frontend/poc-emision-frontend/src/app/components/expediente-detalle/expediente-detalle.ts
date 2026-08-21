import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { PortalShellComponent } from '../portal-shell/portal-shell';
import { CasoDetalle, CasosService, estadoClase } from '../../services/casos';
import { ResultadoValidacion } from '../../services/validacion';

@Component({
  selector: 'app-expediente-detalle',
  standalone: true,
  imports: [CommonModule, PortalShellComponent],
  templateUrl: './expediente-detalle.html',
  styleUrl: './expediente-detalle.scss',
})
export class ExpedienteDetalleComponent implements OnInit {
  folio = '';
  caso: CasoDetalle | null = null;
  cargando = true;
  error = '';
  filtroResultados: 'todos' | 'error' | 'advertencia' = 'todos';
  descargando: string | null = null;

  constructor(
    private route: ActivatedRoute,
    private casosSvc: CasosService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    this.folio = this.route.snapshot.paramMap.get('folio') ?? '';
    this.cargar();
  }

  cargar(): void {
    this.cargando = true;
    this.error = '';
    this.casosSvc.obtenerCaso(this.folio).subscribe({
      next: (caso) => {
        this.caso = caso;
        this.cargando = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.error = `No se encontró el expediente ${this.folio}.`;
        this.cargando = false;
        this.cdr.markForCheck();
      },
    });
  }

  get resultadosFiltrados(): ResultadoValidacion[] {
    const resultados = this.caso?.reporte?.resultados ?? [];
    if (this.filtroResultados === 'todos') {
      return resultados;
    }
    return resultados.filter((resultado) => resultado.tipo === this.filtroResultados);
  }

  get totalErrores(): number {
    return this.caso?.reporte?.resultados.filter((r) => r.tipo === 'error').length ?? 0;
  }

  get totalAdvertencias(): number {
    return this.caso?.reporte?.resultados.filter((r) => r.tipo === 'advertencia').length ?? 0;
  }

  setFiltro(filtro: 'todos' | 'error' | 'advertencia'): void {
    this.filtroResultados = filtro;
  }

  estadoClase(estado: string): string {
    return estadoClase(estado);
  }

  obtenerClaseResultado(tipo: ResultadoValidacion['tipo']): string {
    return tipo === 'advertencia' ? 'advertencia' : 'error';
  }

  formatoBytes(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  descargar(nombre: string): void {
    if (!this.caso) {
      return;
    }
    this.descargando = nombre;
    this.casosSvc.descargarDocumento(this.caso.folio, nombre).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const enlace = document.createElement('a');
        enlace.href = url;
        enlace.download = nombre;
        enlace.click();
        URL.revokeObjectURL(url);
        this.descargando = null;
        this.cdr.markForCheck();
      },
      error: () => {
        this.descargando = null;
        this.cdr.markForCheck();
      },
    });
  }
}