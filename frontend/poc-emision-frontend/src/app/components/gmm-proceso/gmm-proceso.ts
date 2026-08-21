import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, ElementRef, Input, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpEventType, HttpResponse } from '@angular/common/http';
import { Router } from '@angular/router';
import { Subscription, finalize, timeout } from 'rxjs';
import { PortalShellComponent } from '../portal-shell/portal-shell';
import { CONFIGURACION_PROCESO } from '../shared/portal-data';
import { ReporteValidacion, ResultadoValidacion, TipoAccion, ValidacionService } from '../../services/validacion';
import { CasosService, ESTADOS_CERRADOS } from '../../services/casos';
import { AuthService } from '../../services/auth';

type EstadoRevision = 'idle' | 'analizando' | 'listo' | 'error';

@Component({
  selector: 'app-gmm-proceso',
  standalone: true,
  imports: [CommonModule, FormsModule, PortalShellComponent],
  templateUrl: './gmm-proceso.html',
  styleUrl: './gmm-proceso.scss',
})
export class GmmProcesoComponent implements OnInit, OnDestroy {
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
  totalAbiertos = 0;

  // Envío del expediente a suscripción interna, una vez validado localmente.
  empresa = '';
  enviando = false;
  envioError = '';
  folioCreado: string | null = null;

  mostrarModalReinicio = false;
  showDownloadOptions = false; // Nueva propiedad: Controla la visibilidad del menú de descarga

  private temporizadorProgreso: ReturnType<typeof setInterval> | null = null;
  private solicitudActiva: Subscription | null = null;

  constructor(
    private validacionSvc: ValidacionService,
    private casosSvc: CasosService,
    private auth: AuthService,
    private router: Router,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    this.casosSvc.listarCasos({ creado_por: this.auth.getUsername() }).subscribe({
      next: (casos) => {
        this.totalAbiertos = casos.filter((c) => !ESTADOS_CERRADOS.includes(c.estado)).length;
        this.cdr.markForCheck();
      },
      error: () => {
        this.totalAbiertos = 0;
        this.cdr.markForCheck();
      },
    });
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

  // El análisis terminó (con o sin errores): ya no tiene sentido seguir
  // mostrando la bandeja de carga, se debe ver el resultado.
  get estaFinalizado(): boolean {
    return this.estadoRevision === 'listo' || this.estadoRevision === 'error';
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

    return `Se encontraron ${this.totalAdvertencias} advertencias en el analisis de la macro.`
  }

  get puedeEnviar(): boolean {
    return !!this.archivo && !!this.empresa.trim() && this.estadoRevision === 'listo' && !this.enviando;
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
    this.folioCreado = null;
    this.envioError = '';
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
          this.cdr.markForCheck();
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
          this.cdr.markForCheck();
          return;
        }

        if (evento.type === HttpEventType.Response) {
          const reporte = (evento as HttpResponse<ReporteValidacion>).body;
          if (!reporte) {
            this.estadoRevision = 'error';
            this.error = 'La respuesta del servidor no incluye el resumen del analisis.';
            this.progresoValidacion = 0;
            this.cdr.markForCheck();
            return;
          }

          this.reporteActual = reporte;
          this.estadoRevision = 'listo';
          this.mostrarResumen = true;
          this.progresoValidacion = 100;
          this.mensajeCarga = 'Analisis completado';
          this.enfocarResumen();
          this.cdr.markForCheck();
        }
      },
      error: (err: { error?: { detail?: string } }) => {
        this.estadoRevision = 'error';
        this.mostrarResumen = false;
        this.error = err?.error?.detail ?? 'No fue posible analizar los datos. Verifica el archivo e intenta de nuevo.';
        this.progresoValidacion = 0;
        this.mensajeCarga = 'No se pudo completar el analisis';
        this.cdr.markForCheck();
      },
    });
  }

  // Pide confirmación antes de descartar el análisis actual (abre el modal
  // de advertencia); evita perder trabajo por un clic accidental.
  solicitarReinicio(): void {
    this.mostrarModalReinicio = true;
  }

  cancelarReinicio(): void {
    this.mostrarModalReinicio = false;
  }

  confirmarReinicio(): void {
    this.mostrarModalReinicio = false;
    this.reiniciarEstado();
  }

  setFiltroResultados(filtro: 'todos' | 'error' | 'advertencia'): void {
    this.filtroResultados = filtro;
  }

  obtenerClaseResultado(tipo: ResultadoValidacion['tipo']): string {
    return tipo === 'advertencia' ? 'advertencia' : 'error';
  }

  enviarASuscripcion(): void {
    if (!this.puedeEnviar || !this.archivo) {
      return;
    }
    this.enviando = true;
    this.envioError = '';

    this.casosSvc.crearCaso(this.archivo, this.empresa.trim(), this.tipoAccion, 'GMM').subscribe({
      next: (caso) => {
        this.enviando = false;
        this.folioCreado = caso.folio;
        this.cdr.markForCheck();
        this.router.navigate(['/expediente', caso.folio]);
      },
      error: (err: { error?: { detail?: string } }) => {
        this.enviando = false;
        this.envioError = err?.error?.detail ?? 'No fue posible enviar el expediente a suscripción.';
        this.cdr.markForCheck();
      },
    });
  }

  toggleDownloadOptions(): void {
    console.log('Toggle download options clicked. Current showDownloadOptions:', this.showDownloadOptions);
    this.showDownloadOptions = !this.showDownloadOptions;
  }

  descargarReporteErrores(formato: 'csv' | 'excel'): void {
    console.log(`Intentando descargar reporte de errores en formato: ${formato}`);

    if (!this.reporteActual || !this.archivo || this.totalErrores === 0) {
      console.warn('Condiciones no cumplidas para la descarga.');
      return;
    }

    this.showDownloadOptions = false; // Cierra el dropdown después de la selección

    // Extraer los números de fila de los errores para enviarlos al backend
    const filasConError = this.reporteActual.resultados
      .filter(resultado => resultado.tipo === 'error' && resultado.fila !== null)
      .map(resultado => resultado.fila as number);

    this.validacionSvc.descargarResultados(
      this.archivo,
      this.tipoAccion,
      'GMM', // El tipo de producto es GMM para este componente
      filasConError,
      formato
    ).subscribe({
      next: (blob: Blob) => { // Añadido tipo Blob
        console.log('Descarga iniciada con éxito. Creando URL para el Blob.');
        // Crear un enlace temporal y simular un clic para descargar el archivo
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const extension = formato === 'excel' ? 'xlsx' : formato;
        a.download = `errores_${this.nombreArchivo.split('.')[0]}.${extension}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        console.log('Archivo descargado y recursos liberados.');
      },
      error: (err: any) => { // Añadido tipo any
        console.error('Error al descargar el reporte de errores:', err);
        this.error = err?.error?.detail ?? 'No fue posible descargar el reporte de errores. Intenta de nuevo.';
        this.cdr.markForCheck();
      }
    });
  }

  private asignarArchivo(archivo: File): void {
    this.reiniciarEstado();
    this.archivo = archivo;
    this.nombreArchivo = archivo.name;
    this.mensajeCarga = 'Archivo cargado, iniciando analisis';

    // El analisis inicia automaticamente al cargar el archivo.
    this.validar();
  }

  // Descarta el archivo/análisis actual y deja el componente como recién
  // montado, listo para recibir un nuevo caso.
  private reiniciarEstado(): void {
    this.cancelarSolicitudActiva();
    this.detenerProgresoSimulado();
    this.archivo = null;
    this.nombreArchivo = '';
    this.error = '';
    this.reporteActual = null;
    this.mostrarResumen = false;
    this.filtroResultados = 'todos';
    this.estadoRevision = 'idle';
    this.progresoValidacion = 0;
    this.mensajeCarga = 'Carga un archivo para iniciar el analisis';
    this.arrastrandoArchivo = false;
    this.folioCreado = null;
    this.envioError = '';
    this.empresa = '';
    this.enviando = false;
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
        this.cdr.markForCheck();
        return;
      }

      if (this.progresoValidacion < 94) {
        this.progresoValidacion += 1;
        this.mensajeCarga = `Analizando datos ${this.progresoBoton}%`;
        this.cdr.markForCheck();
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
