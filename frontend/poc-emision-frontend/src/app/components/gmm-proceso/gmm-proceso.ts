import { CommonModule } from '@angular/common';
import { Component, ElementRef, Input, OnDestroy, ViewChild } from '@angular/core';
import { HttpEventType, HttpResponse } from '@angular/common/http';
import { Subscription, finalize, timeout } from 'rxjs';
import { PortalShellComponent } from '../portal-shell/portal-shell';
import { CONFIGURACION_PROCESO, EXPEDIENTES_MOCK } from '../shared/portal-data';
import { ReporteValidacion, ResultadoValidacion, TipoAccion, ValidacionService } from '../../services/validacion';

type EstadoRevision = 'idle' | 'analizando' | 'listo' | 'error';

@Component({
  selector: 'app-gmm-proceso',
  standalone: true,
  imports: [CommonModule, PortalShellComponent],
  templateUrl: './gmm-proceso.html',
  styleUrl: './gmm-proceso.scss',
})
export class GmmProcesoComponent implements OnDestroy {
  @Input({ required: true }) tipoAccion: TipoAccion = 'nueva';
  @ViewChild('resumenAnalisis') resumenAnalisisRef?: ElementRef<HTMLElement>;

  archivo: File | null = null;
  nombreArchivo = '';
  estadoRevision: EstadoRevision = 'idle';
  progresoValidacion = 0;
  mensajeCarga = 'Carga un archivo para iniciar el analisis';
  error = '';
  reporteActual: ReporteValidacion | null = null;
  mostrarResumen = false;
  filtroResultados: 'todos' | 'error' | 'advertencia' = 'todos';
  arrastrandoArchivo = false;
  private temporizadorProgreso: ReturnType<typeof setInterval> | null = null;
  private solicitudActiva: Subscription | null = null;

  constructor(private validacionSvc: ValidacionService) {}

  get totalAbiertos(): number {
    return EXPEDIENTES_MOCK.filter((expediente) => expediente.estado !== 'Completado').length;
  }

  get configuracionActual() {
    return CONFIGURACION_PROCESO[this.tipoAccion];
  }

  get progresoBoton(): number {
    return Math.max(0, Math.min(100, this.progresoValidacion));
  }

  get estaAnalizando(): boolean {
    return this.estadoRevision === 'analizando';
  }

  get archivoCargado(): boolean {
    return !!this.archivo;
  }

  get estadoTexto(): string {
    if (this.estadoRevision === 'analizando') {
      return `Analizando datos ${this.progresoBoton}%`;
    }

    if (this.estadoRevision === 'listo') {
      return 'Analisis completado';
    }

    if (this.estadoRevision === 'error') {
      return 'No se pudo completar el analisis';
    }

    return 'En espera de archivo';
  }

  get resultadosFiltrados(): ResultadoValidacion[] {
    if (!this.reporteActual) {
      return [];
    }

    if (this.filtroResultados === 'todos') {
      return this.reporteActual.resultados;
    }

    return this.reporteActual.resultados.filter((resultado) => resultado.tipo === this.filtroResultados);
  }

  get totalErrores(): number {
    return this.reporteActual?.resultados.filter((resultado) => resultado.tipo === 'error').length ?? 0;
  }

  get totalAdvertencias(): number {
    return this.reporteActual?.resultados.filter((resultado) => resultado.tipo === 'advertencia').length ?? 0;
  }

  get resumenHallazgos(): string {
    if (!this.reporteActual) {
      return '';
    }

    if (this.reporteActual.resumen.es_valida) {
      return 'No se encontraron errores bloqueantes en la macro cargada.';
    }

    if (this.totalErrores > 0 && this.totalAdvertencias > 0) {
      return `Se encontraron ${this.totalErrores} errores y ${this.totalAdvertencias} advertencias en el analisis.`;
    }

    if (this.totalErrores > 0) {
      return `Se encontraron ${this.totalErrores} errores en el analisis de la macro.`;
    }

    return `Se encontraron ${this.totalAdvertencias} advertencias en el analisis de la macro.`;
  }

  get botonDeshabilitado(): boolean {
    return !this.archivo || this.estaAnalizando;
  }

  get etiquetaBoton(): string {
    if (this.estaAnalizando) {
      return `Analizando ${this.progresoBoton}%`;
    }

    if (this.estadoRevision === 'listo') {
      return 'Analizar de nuevo';
    }

    return 'Analizar datos';
  }

  ngOnDestroy(): void {
    this.detenerProgresoSimulado();
    this.cancelarSolicitudActiva();
  }

  onArchivoSeleccionado(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files?.length) {
      this.asignarArchivo(input.files[0]);
    }
  }

  onDragOver(event: DragEvent): void {
    if (this.estaAnalizando) {
      return;
    }
    event.preventDefault();
    this.arrastrandoArchivo = true;
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    this.arrastrandoArchivo = false;
  }

  onDropArchivo(event: DragEvent): void {
    if (this.estaAnalizando) {
      return;
    }
    event.preventDefault();
    this.arrastrandoArchivo = false;

    const archivo = event.dataTransfer?.files?.[0];
    if (archivo) {
      this.asignarArchivo(archivo);
    }
  }

  validar(): void {
    if (!this.archivo || this.estaAnalizando) {
      return;
    }

    this.cancelarSolicitudActiva();
    this.estadoRevision = 'analizando';
    this.error = '';
    this.reporteActual = null;
    this.mostrarResumen = false;
    this.filtroResultados = 'todos';
    this.progresoValidacion = 6;
    this.mensajeCarga = 'Cargando datos 8%';
    this.iniciarProgresoSimulado();

    this.solicitudActiva = this.validacionSvc.validarMacro(this.archivo, this.tipoAccion, 'GMM').pipe(
      timeout(120000),
      finalize(() => {
        this.detenerProgresoSimulado();
        if (this.estadoRevision === 'analizando') {
          this.estadoRevision = 'error';
          this.error = 'La revision no pudo completarse. Intenta de nuevo.';
          this.progresoValidacion = 0;
          this.mensajeCarga = 'No se pudo completar el analisis';
        }
      }),
    ).subscribe({
      next: (evento) => {
        if (evento.type === HttpEventType.UploadProgress) {
          const total = evento.total ?? evento.loaded;
          const porcentajeCarga = total > 0
            ? Math.round((evento.loaded / total) * 70)
            : Math.min(70, this.progresoValidacion + 5);

          this.progresoValidacion = Math.max(this.progresoValidacion, porcentajeCarga);
          this.mensajeCarga = `Cargando datos ${this.progresoBoton}%`;
          return;
        }

        if (evento.type === HttpEventType.Response) {
          const reporte = (evento as HttpResponse<ReporteValidacion>).body;
          if (!reporte) {
            this.estadoRevision = 'error';
            this.error = 'La respuesta del servidor no incluye el resumen del analisis.';
            this.progresoValidacion = 0;
            return;
          }

          this.reporteActual = reporte;
          this.estadoRevision = 'listo';
          this.mostrarResumen = true;
          this.progresoValidacion = 100;
          this.mensajeCarga = 'Analisis completado';
          this.enfocarResumen();
        }
      },
      error: (err: { error?: { detail?: string } }) => {
        this.estadoRevision = 'error';
        this.mostrarResumen = false;
        this.error = err?.error?.detail ?? 'No fue posible analizar los datos. Verifica el archivo e intenta de nuevo.';
        this.progresoValidacion = 0;
        this.mensajeCarga = 'No se pudo completar el analisis';
      },
    });
  }

  setFiltroResultados(filtro: 'todos' | 'error' | 'advertencia'): void {
    this.filtroResultados = filtro;
  }

  obtenerClaseResultado(tipo: ResultadoValidacion['tipo']): string {
    return tipo === 'advertencia' ? 'advertencia' : 'error';
  }

  private asignarArchivo(archivo: File): void {
    this.cancelarSolicitudActiva();
    this.archivo = archivo;
    this.nombreArchivo = archivo.name;
    this.error = '';
    this.reporteActual = null;
    this.mostrarResumen = false;
    this.estadoRevision = 'idle';
    this.progresoValidacion = 0;
    this.mensajeCarga = 'Archivo cargado, iniciando analisis';
    this.arrastrandoArchivo = false;

    // El analisis inicia automaticamente al cargar el archivo.
    this.validar();
  }

  private iniciarProgresoSimulado(): void {
    this.detenerProgresoSimulado();

    this.temporizadorProgreso = setInterval(() => {
      if (!this.estaAnalizando) {
        this.detenerProgresoSimulado();
        return;
      }

      if (this.progresoValidacion < 78) {
        this.progresoValidacion += 3;
        this.mensajeCarga = `Cargando datos ${this.progresoBoton}%`;
        return;
      }

      if (this.progresoValidacion < 94) {
        this.progresoValidacion += 1;
        this.mensajeCarga = `Analizando datos ${this.progresoBoton}%`;
      }
    }, 180);
  }

  private cancelarSolicitudActiva(): void {
    if (this.solicitudActiva) {
      this.solicitudActiva.unsubscribe();
      this.solicitudActiva = null;
    }
  }

  private detenerProgresoSimulado(): void {
    if (this.temporizadorProgreso) {
      clearInterval(this.temporizadorProgreso);
      this.temporizadorProgreso = null;
    }
  }

  private enfocarResumen(): void {
    setTimeout(() => {
      this.resumenAnalisisRef?.nativeElement.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      });
    }, 0);
  }
}