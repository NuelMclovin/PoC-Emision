import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { PortalShellComponent } from '../portal-shell/portal-shell';
import { AuthService } from '../../services/auth';
import { CasoDetalle, CasosService, EstadoCaso, estadoClase } from '../../services/casos';
import { ResultadoValidacion } from '../../services/validacion';

@Component({
  selector: 'app-caso-detalle',
  standalone: true,
  imports: [CommonModule, FormsModule, PortalShellComponent],
  templateUrl: './caso-detalle.html',
  styleUrl: './caso-detalle.scss',
})
export class CasoDetalleComponent implements OnInit {
  folio = '';
  caso: CasoDetalle | null = null;
  cargando = true;
  error = '';
  filtroResultados: 'todos' | 'error' | 'advertencia' = 'todos';

  comentario = '';
  procesando = false;
  accionError = '';
  descargando: string | null = null;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private casosSvc: CasosService,
    private auth: AuthService,
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
        this.comentario = caso.comentario_suscriptor || '';
        this.cargando = false;
      },
      error: () => {
        this.error = `No se encontró el expediente ${this.folio}.`;
        this.cargando = false;
      },
    });
  }

  get resultadosFiltrados(): ResultadoValidacion[] {
    const resultados = this.caso?.reporte?.resultados ?? [];
    if (this.filtroResultados === 'todos') {
      return resultados;
    }
    return resultados.filter((r) => r.tipo === this.filtroResultados);
  }

  get totalErrores(): number {
    return this.caso?.reporte?.resultados.filter((r) => r.tipo === 'error').length ?? 0;
  }

  get totalAdvertencias(): number {
    return this.caso?.reporte?.resultados.filter((r) => r.tipo === 'advertencia').length ?? 0;
  }

  get puedeTomar(): boolean {
    return this.caso?.estado === 'Pendiente';
  }

  get puedeResolver(): boolean {
    return !!this.caso && (this.caso.estado === 'En revisión' || this.caso.estado === 'Observado');
  }

  get soyResponsable(): boolean {
    return !!this.caso && this.caso.asignado_a === this.auth.getUsername();
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

  tomarCaso(): void {
    if (!this.caso) {
      return;
    }
    this.procesando = true;
    this.accionError = '';
    this.casosSvc.actualizarCaso(this.caso.folio, { estado: 'En revisión' }).subscribe({
      next: (caso) => {
        this.caso = caso;
        this.procesando = false;
      },
      error: () => {
        this.procesando = false;
        this.accionError = 'No se pudo tomar el caso. Intenta de nuevo.';
      },
    });
  }

  resolver(estado: EstadoCaso): void {
    if (!this.caso) {
      return;
    }
    this.procesando = true;
    this.accionError = '';
    this.casosSvc.actualizarCaso(this.caso.folio, { estado, comentario_suscriptor: this.comentario }).subscribe({
      next: (caso) => {
        this.caso = caso;
        this.procesando = false;
      },
      error: (err: { error?: { detail?: string } }) => {
        this.procesando = false;
        this.accionError = err?.error?.detail ?? 'No se pudo actualizar el caso.';
      },
    });
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
      },
      error: () => {
        this.descargando = null;
      },
    });
  }

  volver(): void {
    this.router.navigate(['/bandeja']);
  }
}