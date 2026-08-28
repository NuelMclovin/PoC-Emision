import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, ElementRef, Input, OnDestroy, ViewChild } from '@angular/core';
import { HttpEventType, HttpResponse } from '@angular/common/http';
import { Subscription, finalize, timeout } from 'rxjs';
import { PortalShellComponent } from '../portal-shell/portal-shell';
import { CONFIGURACION_PROCESO, EXPEDIENTES_MOCK } from '../shared/portal-data';
import { ReporteValidacion, ResultadoValidacion, TipoAccion, ValidacionService } from '../../services/validacion';
import { FormsModule } from '@angular/forms';

type EstadoRevision = 'idle' | 'analizando' | 'listo' | 'error';
// Nuevo tipo para las etapas del flujo de renovación
type EtapaRenovacion = 'cargandoBase' | 'baseValidada' | 'cargandoNuevo' | 'comparando' | 'renovacionCompletada' | 'errorRenovacion';


@Component({
  selector: 'app-gmm-proceso',
  standalone: true,
  imports: [CommonModule, PortalShellComponent, FormsModule],
  templateUrl: './gmm-proceso.html',
  styleUrls: ['./gmm-proceso.scss'],
})
export class GmmProcesoComponent implements OnDestroy {
  @Input({ required: true }) tipoAccion: TipoAccion = 'nueva';
  @ViewChild('resumenAnalisis') resumenAnalisisRef?: ElementRef<HTMLElement>;

  // --- Propiedades para el archivo "actual" o "nuevo" (el que se valida o compara) ---
  archivo: File | null = null;
  nombreArchivo = '';
  estadoRevision: EstadoRevision = 'idle';
  progresoValidacion = 0;
  mensajeCarga = 'Carga un archivo para iniciar el analisis'; // Mensaje principal
  error = '';
  reporteActual: ReporteValidacion | null = null;
  mostrarResumen = false;
  filtroResultados: 'todos' | 'error' | 'advertencia' = 'todos';
  filtroTipoColumna: 'todos' | ResultadoValidacion['tipo'] = 'todos';
  filtroMovimiento = 'todos';
  filtroCategoria = 'todos';
  arrastrandoArchivo = false;

  private temporizadorProgreso: ReturnType<typeof setInterval> | null = null;
  private solicitudActiva: Subscription | null = null;

  // --- NUEVAS PROPIEDADES ESPECÍFICAS PARA EL FLUJO DE RENOVACIÓN ---
  archivoBase: File | null = null;
  nombreArchivoBase = '';
  reporteBase: ReporteValidacion | null = null;
  estadoRevisionBase: EstadoRevision = 'idle';
  progresoValidacionBase = 0;
  errorBase = '';
  mensajeCargaBase = 'Carga el archivo base para la renovación'; // Mensaje para el archivo base

  // Controla la etapa actual del proceso de renovación
  etapaRenovacion: EtapaRenovacion = 'cargandoBase';

  // Nuevo para export
  exportFormato: 'csv' | 'xlsx' = 'csv';
  encabezados: string[] = [];
  filasConErrores: any[] = [];

  constructor(
    private validacionSvc: ValidacionService,
    private cdr: ChangeDetectorRef,
  ) {}

  get totalAbiertos(): number {
    return EXPEDIENTES_MOCK.filter((expediente) => expediente.estado !== 'Completado').length;
  }

  get configuracionActual() {
    return CONFIGURACION_PROCESO[this.tipoAccion];
  }

  // Progreso para el archivo "actual" o "nuevo"
  get progresoBoton(): number {
    return Math.max(0, Math.min(100, this.progresoValidacion));
  }

  // NUEVO: Progreso para el archivo base
  get progresoBotonBase(): number {
    return Math.max(0, Math.min(100, this.progresoValidacionBase));
  }

  // Indica si algún análisis está en curso (ya sea del archivo base o del nuevo)
  get estaAnalizando(): boolean {
    if (this.tipoAccion === 'nueva') {
      return this.estadoRevision === 'analizando';
    }
    return this.estadoRevisionBase === 'analizando' || this.estadoRevision === 'analizando';
  }

  // Indica si un archivo ha sido cargado (para el proceso actual)
  get archivoCargado(): boolean {
    return !!this.archivo;
  }

  // NUEVO: Indica si el archivo base ha sido cargado
  get archivoBaseCargado(): boolean {
    return !!this.archivoBase;
  }

  // Mensaje de estado principal
  get estadoTexto(): string {
    if (this.tipoAccion === 'nueva') {
      if (this.estadoRevision === 'analizando') return `Analizando datos ${this.progresoBoton}%`;
      if (this.estadoRevision === 'listo') return 'Análisis completado';
      if (this.estadoRevision === 'error') return this.error || 'No se pudo completar el análisis';
      return 'Carga un archivo para iniciar el análisis';
    } else { // tipoAccion === 'renovacion'
      switch (this.etapaRenovacion) {
        case 'cargandoBase':
          if (this.estadoRevisionBase === 'analizando') return `Analizando archivo base ${this.progresoBotonBase}%`;
          if (this.estadoRevisionBase === 'error') return this.errorBase || 'Error en validación de archivo base';
          return this.mensajeCargaBase; // "Carga el archivo base para la renovación"
        case 'baseValidada':
          if (this.estadoRevision === 'analizando') return `Analizando nuevo archivo ${this.progresoBoton}%`;
          if (this.estadoRevision === 'error') return this.error || 'Error en validación del nuevo archivo';
          return this.mensajeCarga; // "Archivo base validado. Carga el nuevo archivo de renovación."
        case 'comparando':
            return `Comparando archivos ${this.progresoBoton}%`;
        case 'renovacionCompletada':
          return 'Comparación de renovación completada';
        case 'errorRenovacion':
          return this.error || 'Error en el proceso de renovación';
        default:
          return 'Esperando inicio del proceso de renovación';
      }
    }
  }

  get resultadosFiltrados(): ResultadoValidacion[] {
    if (!this.reporteActual) {
      return [];
    }

    return this.reporteActual.resultados.filter((resultado) => {
      const coincideTipoColumna = this.filtroTipoColumna === 'todos' || resultado.tipo === this.filtroTipoColumna;
      const movimiento = resultado.tipo_movimiento ?? '';
      const coincideMovimiento = this.filtroMovimiento === 'todos' || movimiento === this.filtroMovimiento;
      const columnas = this.columnasDelResultado(resultado);
      const coincideColumna = this.filtroCategoria === 'todos' || columnas.includes(this.filtroCategoria);
      return coincideTipoColumna && coincideMovimiento && coincideColumna;
    });
  }

  get opcionesTiposResultado(): ResultadoValidacion['tipo'][] {
    return this.opcionesUnicas(this.resultadosSinFiltro('tipo').map((resultado) => resultado.tipo)) as ResultadoValidacion['tipo'][];
  }

  get opcionesMovimientos(): string[] {
    return this.opcionesUnicas(this.resultadosSinFiltro('movimiento').map((resultado) => resultado.tipo_movimiento).filter(Boolean) as string[]);
  }

  get opcionesCategorias(): string[] {
    return this.opcionesUnicas(this.resultadosSinFiltro('categoria').flatMap((resultado) => this.columnasDelResultado(resultado)));
  }

  columnasDelResultado(resultado: ResultadoValidacion): string[] {
    return resultado.columnas_afectadas?.length
      ? resultado.columnas_afectadas
      : resultado.columna
        ? [resultado.columna]
        : [];
  }

  private resultadosSinFiltro(excluir: 'tipo' | 'movimiento' | 'categoria'): ResultadoValidacion[] {
    return (this.reporteActual?.resultados ?? []).filter((resultado) => {
      const coincideTipo = excluir === 'tipo' || this.filtroTipoColumna === 'todos' || resultado.tipo === this.filtroTipoColumna;
      const movimiento = resultado.tipo_movimiento ?? '';
      const coincideMovimiento = excluir === 'movimiento' || this.filtroMovimiento === 'todos' || movimiento === this.filtroMovimiento;
      const coincideColumna = excluir === 'categoria' || this.filtroCategoria === 'todos' || this.columnasDelResultado(resultado).includes(this.filtroCategoria);
      return coincideTipo && coincideMovimiento && coincideColumna;
    });
  }

  private opcionesUnicas(valores: string[]): string[] {
    return [...new Set(valores)].sort((a, b) => a.localeCompare(b));
  }

  etiquetaTipoResultado(tipo: ResultadoValidacion['tipo']): string {
    return tipo === 'error' ? 'Error' : tipo === 'advertencia' ? 'Advertencia' : 'Información';
  }

  get totalErrores(): number {
    return this.reporteActual?.resultados.filter((resultado: ResultadoValidacion) => resultado.tipo === 'error').length ?? 0;
  }

  get totalAdvertencias(): number {
    return this.reporteActual?.resultados.filter((resultado: ResultadoValidacion) => resultado.tipo === 'advertencia').length ?? 0;
  }

  get totalRegistrosConCambios(): number {
    return new Set(
      this.reporteActual?.resultados
        .filter((resultado) => resultado.tipo_movimiento === 'Cambio')
        .map((resultado) => resultado.fila ?? resultado.valor),
    ).size;
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

  // Controla la habilitación del botón principal "Validar"
  get botonDeshabilitado(): boolean {
    if (this.estaAnalizando) {
      return true; // Deshabilitar si cualquier análisis está en curso
    }
    if (this.tipoAccion === 'nueva') {
      return !this.archivo;
    } else { // tipoAccion === 'renovacion'
      if (this.etapaRenovacion === 'cargandoBase') {
        return !this.archivoBase;
      }
      if (this.etapaRenovacion === 'baseValidada') {
        return !this.archivo; // Deshabilitado hasta que se cargue el nuevo archivo
      }
      // 'cargandoNuevo', 'comparando', 'renovacionCompletada', 'errorRenovacion'
      return false; // El botón "Validar y Comparar" estará habilitado una vez que ambos estén cargados
    }
  }

  // Etiqueta del botón principal "Validar"
  get etiquetaBoton(): string {
    if (this.estaAnalizando) {
      // Mostrar el progreso del análisis actual
      const progreso = (this.estadoRevisionBase === 'analizando' ? this.progresoBotonBase : this.progresoBoton);
      return `Analizando ${progreso}%`;
    }

    if (this.tipoAccion === 'nueva') {
      return this.estadoRevision === 'listo' ? 'Analizar de nuevo' : 'Analizar datos';
    } else { // tipoAccion === 'renovacion'
      switch (this.etapaRenovacion) {
        case 'cargandoBase':
          return 'Validar archivo base';
        case 'baseValidada':
          return this.archivo ? 'Validar y comparar' : 'Carga el nuevo archivo';
        case 'renovacionCompletada':
        case 'errorRenovacion':
          return 'Comparar de nuevo';
        default:
          return 'Iniciar renovación';
      }
    }
  }

  ngOnDestroy(): void {
    this.detenerProgresoSimulado(false); // Detener para archivo actual
    this.detenerProgresoSimulado(true);  // Detener para archivo base
    this.cancelarSolicitudActiva();
  }

  onArchivoSeleccionado(event: Event, esArchivoBase: boolean = false): void {
    const input = event.target as HTMLInputElement;
    if (input.files?.length) {
      this.asignarArchivo(input.files[0], esArchivoBase);
      // Resetear el input para permitir cargar el mismo archivo de nuevo si es necesario
      input.value = '';
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

  onDropArchivo(event: DragEvent, esArchivoBase: boolean = false): void {
    if (this.estaAnalizando) {
      return;
    }
    event.preventDefault();
    this.arrastrandoArchivo = false;

    const archivo = event.dataTransfer?.files?.[0];
    if (archivo) {
      this.asignarArchivo(archivo, esArchivoBase);
    }
  }

  // Método principal que orquesta la validación
  validar(): void {
    if (this.estaAnalizando) {
        return; // No hacer nada si ya hay un análisis en curso
    }

    if (this.tipoAccion === 'nueva') {
      this.iniciarValidacionSimple();
    } else if (this.tipoAccion === 'renovacion') {
      this.iniciarFlujoRenovacion();
    }
  }

  private iniciarValidacionSimple(): void {
    if (!this.archivo) {
      this.error = 'Por favor, carga un archivo para iniciar la validación.';
      this.estadoRevision = 'error';
      return;
    }
    this.ejecutarValidacion(this.archivo, false);
  }

  private iniciarFlujoRenovacion(): void {
    switch (this.etapaRenovacion) {
      case 'cargandoBase':
        if (!this.archivoBase) {
          this.errorBase = 'Por favor, carga el archivo base para la renovación.';
          this.estadoRevisionBase = 'error';
          return;
        }
        this.ejecutarValidacion(this.archivoBase, true);
        break;
      case 'baseValidada':
        if (!this.archivo) {
          this.error = 'Por favor, carga el nuevo archivo de renovación para comparar.';
          this.estadoRevision = 'error';
          return;
        }
        this.ejecutarComparacionRenovacion(this.archivo, this.archivoBase!);
        break;
      case 'renovacionCompletada':
      case 'errorRenovacion':
          // Si ya se completó o hubo un error, se puede re-ejecutar la comparación si ambos archivos están presentes
          if (this.archivo && this.archivoBase) {
            this.ejecutarComparacionRenovacion(this.archivo, this.archivoBase);
          } else {
            this.etapaRenovacion = 'cargandoBase'; // Reiniciar el flujo si no hay archivos
            this.resetearEstados();
          }
          break;
      default:
        console.warn('Intento de validación de renovación en etapa inesperada:', this.etapaRenovacion);
        this.error = 'Ocurrió un error inesperado en el flujo de renovación.';
        this.estadoRevision = 'error';
        this.etapaRenovacion = 'errorRenovacion';
        break;
    }
  }

  // Método unificado para ejecutar la validación de un archivo (ya sea base o nuevo)
  private ejecutarValidacion(fileToValidate: File, isBaseFile: boolean): void {
    this.cancelarSolicitudActiva();

    // Resetear estados relevantes
    if (isBaseFile) {
      this.estadoRevisionBase = 'analizando';
      this.errorBase = '';
      this.reporteBase = null;
      this.progresoValidacionBase = 6;
      this.mensajeCargaBase = `Cargandoarchivo base ${this.progresoBotonBase}%`;
    } else {
      this.estadoRevision = 'analizando';
      this.error = '';
      this.reporteActual = null;
      this.mostrarResumen = false;
      this.filtroResultados = 'todos';
      this.limpiarFiltrosColumnas();
      this.progresoValidacion = 6;
      this.mensajeCarga = `Cargando datos ${this.progresoBoton}%`;
    }
    this.iniciarProgresoSimulado(isBaseFile);

    const validacion$ = isBaseFile
      ? this.validacionSvc.validarBaseRenovacion(fileToValidate)
      : this.validacionSvc.validarMacro(fileToValidate, this.tipoAccion, 'GMM');

    this.solicitudActiva = validacion$.pipe(
      timeout(120000),
      finalize(() => {
        this.detenerProgresoSimulado(isBaseFile);
        const currentEstado = isBaseFile ? this.estadoRevisionBase : this.estadoRevision;
        if (currentEstado === 'analizando') { // Si la solicitud se canceló o finalizó sin una respuesta de éxito
          if (isBaseFile) {
            this.estadoRevisionBase = 'error';
            this.errorBase = 'La revisión del archivo base no pudo completarse. Intenta de nuevo.';
            this.progresoValidacionBase = 0;
            this.mensajeCargaBase = 'No se pudo completar el análisis del archivo base';
            this.etapaRenovacion = 'errorRenovacion';
          } else {
            this.estadoRevision = 'error';
            this.error = 'La revisión del nuevo archivo no pudo completarse. Intenta de nuevo.';
            this.progresoValidacion = 0;
            this.mensajeCarga = 'No se pudo completar el análisis del nuevo archivo';
            this.etapaRenovacion = 'errorRenovacion';
          }
        }
        this.cdr.detectChanges();
      }),
    ).subscribe({
      next: (evento) => {
        if (evento.type === HttpEventType.UploadProgress) {
          const total = evento.total ?? evento.loaded;
          const porcentajeCarga = total > 0
            ? Math.round((evento.loaded / total) * 70)
            : Math.min(70, isBaseFile ? this.progresoValidacionBase : this.progresoValidacion + 5);

          if (isBaseFile) {
            this.progresoValidacionBase = Math.max(this.progresoValidacionBase, porcentajeCarga);
            this.mensajeCargaBase = `Cargando archivo base ${this.progresoBotonBase}%`;
          } else {
            this.progresoValidacion = Math.max(this.progresoValidacion, porcentajeCarga);
            this.mensajeCarga = `Cargando datos ${this.progresoBoton}%`;
          }
          return;
        }

        if (evento.type === HttpEventType.Response) {
          const reporte = (evento as HttpResponse<ReporteValidacion>).body;
          if (!reporte) {
            if (isBaseFile) {
              this.estadoRevisionBase = 'error';
              this.errorBase = 'La respuesta del servidor no incluye el resumen del análisis del archivo base.';
              this.progresoValidacionBase = 0;
              this.etapaRenovacion = 'errorRenovacion';
            } else {
              this.estadoRevision = 'error';
              this.error = 'La respuesta del servidor no incluye el resumen del análisis del nuevo archivo.';
              this.progresoValidacion = 0;
              this.etapaRenovacion = 'errorRenovacion';
            }
            return;
          }

          if (isBaseFile) {
            this.reporteBase = reporte;
            if (reporte.resumen.total_errores > 0) {
              this.estadoRevisionBase = 'error';
              this.errorBase = 'El archivo base contiene errores y no puede ser usado para la renovación.';
              this.etapaRenovacion = 'cargandoBase'; // Quedarse en esta etapa si la base es inválida
            } else {
              this.estadoRevisionBase = 'listo';
              this.progresoValidacionBase = 100;
              this.mensajeCargaBase = 'Análisis del archivo base completado';
              this.etapaRenovacion = 'baseValidada'; // Mover a la siguiente etapa
              this.mensajeCarga = 'Archivo base validado. Carga el nuevo archivo de renovación.'; // Actualizar mensaje principal
            }
          } else { // Validación del nuevo archivo (en modo "nueva" o después de comparar en "renovacion")
            this.reporteActual = reporte;
            this.encabezados = reporte.encabezados ?? [];
            this.filasConErrores = reporte.filas_con_errores ?? [];

            this.estadoRevision = 'listo';
            this.mostrarResumen = true;
            this.progresoValidacion = 100;
            this.mensajeCarga = 'Análisis completado';
            this.enfocarResumen();
            // Si estábamos en flujo de renovación, ahora se completó
            if (this.tipoAccion === 'renovacion') {
                this.etapaRenovacion = 'renovacionCompletada';
            }
          }
        }
      },
      error: (err: { error?: { detail?: string } }) => {
        if (isBaseFile) {
          this.estadoRevisionBase = 'error';
          this.errorBase = err?.error?.detail ?? 'No fue posible analizar el archivo base. Verifica e intenta de nuevo.';
          this.progresoValidacionBase = 0;
          this.mensajeCargaBase = 'No se pudo completar el análisis del archivo base';
          this.etapaRenovacion = 'errorRenovacion';
        } else {
          this.estadoRevision = 'error';
          this.mostrarResumen = false;
          this.error = err?.error?.detail ?? 'No fue posible analizar el nuevo archivo. Verifica e intenta de nuevo.';
          this.progresoValidacion = 0;
          this.mensajeCarga = 'No se pudo completar el análisis del nuevo archivo';
          this.etapaRenovacion = 'errorRenovacion';
        }
        this.cdr.detectChanges();
      },
    });
  }

  // NUEVO: Método para ejecutar la comparación de archivos de renovación
  private ejecutarComparacionRenovacion(archivoNuevo: File, archivoBase: File): void {
    this.cancelarSolicitudActiva();

    this.estadoRevision = 'analizando'; // El estado principal reflejará la comparación
    this.error = '';
    this.reporteActual = null;
    this.mostrarResumen = false;
    this.filtroResultados = 'todos';
    this.limpiarFiltrosColumnas();
    this.progresoValidacion = 6;
    this.mensajeCarga = 'Cargando y comparando archivos...';
    this.etapaRenovacion = 'comparando';
    this.iniciarProgresoSimulado(false); // Progreso para el archivo "nuevo" / comparación

    this.solicitudActiva = this.validacionSvc.validarYCompararMacro(archivoNuevo, archivoBase, this.tipoAccion, 'GMM').pipe(
      timeout(120000),
      finalize(() => {
        this.detenerProgresoSimulado(false);
        if (this.estadoRevision === 'analizando') {
          this.estadoRevision = 'error';
          this.error = 'La comparación no pudo completarse. Intenta de nuevo.';
          this.progresoValidacion = 0;
          this.mensajeCarga = 'No se pudo completar la comparación';
          this.etapaRenovacion = 'errorRenovacion';
        }
        this.cdr.detectChanges();
      }),
    ).subscribe({
      next: (evento) => {
        if (evento.type === HttpEventType.UploadProgress) {
          const total = evento.total ?? evento.loaded;
          const porcentajeCarga = total > 0
            ? Math.round((evento.loaded / total) * 70)
            : Math.min(70, this.progresoValidacion + 5);

          this.progresoValidacion = Math.max(this.progresoValidacion, porcentajeCarga);
          this.mensajeCarga = `Cargando y comparando ${this.progresoBoton}%`;
          return;
        }

        if (evento.type === HttpEventType.Response) {
          const reporte = (evento as HttpResponse<ReporteValidacion>).body;
          if (!reporte) {
            this.estadoRevision = 'error';
            this.error = 'La respuesta del servidor no incluye el resumen de la comparación.';
            this.progresoValidacion = 0;
            this.etapaRenovacion = 'errorRenovacion';
            return;
          }

          this.reporteActual = reporte;
          this.encabezados = reporte.encabezados ?? [];
          this.filasConErrores = reporte.filas_con_errores ?? [];

          this.estadoRevision = 'listo';
          this.mostrarResumen = true;
          this.progresoValidacion = 100;
          this.mensajeCarga = 'Comparación completada';
          this.enfocarResumen();
          this.etapaRenovacion = 'renovacionCompletada';
        }
      },
      error: (err: { error?: { detail?: string } }) => {
        this.estadoRevision = 'error';
        this.mostrarResumen = false;
        this.error = err?.error?.detail ?? 'No fue posible comparar los archivos. Verifica e intenta de nuevo.';
        this.progresoValidacion = 0;
        this.mensajeCarga = 'No se pudo completar la comparación';
        this.etapaRenovacion = 'errorRenovacion';
        this.cdr.detectChanges();
      },
    });
  }

  setFiltroResultados(filtro: 'todos' | 'error' | 'advertencia'): void {
    this.filtroResultados = filtro;
    this.filtroTipoColumna = filtro;
  }

  actualizarFiltroTipo(tipo: 'todos' | ResultadoValidacion['tipo']): void {
    this.filtroTipoColumna = tipo;
    this.filtroResultados = tipo === 'error' || tipo === 'advertencia' ? tipo : 'todos';
    this.ajustarFiltroMovimiento();
    this.ajustarFiltroCategoria();
  }

  actualizarFiltroMovimiento(movimiento: string): void {
    this.filtroMovimiento = movimiento;
    this.ajustarFiltroCategoria();
  }

  actualizarFiltroCategoria(categoria: string): void {
    this.filtroCategoria = categoria;
    this.ajustarFiltroMovimiento();
  }

  private ajustarFiltroMovimiento(): void {
    const opciones = this.opcionesMovimientos;
    if (this.filtroMovimiento !== 'todos' && !opciones.includes(this.filtroMovimiento)) {
      this.filtroMovimiento = 'todos';
    }
  }

  private ajustarFiltroCategoria(): void {
    const opciones = this.opcionesCategorias;
    if (this.filtroCategoria !== 'todos' && !opciones.includes(this.filtroCategoria)) {
      this.filtroCategoria = 'todos';
    }
  }

  limpiarFiltrosColumnas(): void {
    this.filtroTipoColumna = 'todos';
    this.filtroMovimiento = 'todos';
    this.filtroCategoria = 'todos';
  }

  obtenerClaseResultado(tipo: ResultadoValidacion['tipo']): string {
    return tipo === 'advertencia' ? 'advertencia' : tipo === 'info' ? 'info' : 'error';
  }

  // Modificado para aceptar un flag `esArchivoBase`
  private asignarArchivo(archivo: File, esArchivoBase: boolean): void {
    this.cancelarSolicitudActiva(); // Cancela cualquier solicitud activa

    if (esArchivoBase) {
      this.archivoBase = archivo;
      this.nombreArchivoBase = archivo.name;
      this.errorBase = '';
      this.reporteBase = null;
      this.estadoRevisionBase = 'idle';
      this.progresoValidacionBase = 0;
      this.mensajeCargaBase = 'Archivo base cargado, listo para validar';
      // Si se carga una nueva base, resetear el archivo "nuevo"
      this.archivo = null;
      this.nombreArchivo = '';
      this.reporteActual = null;
      this.estadoRevision = 'idle';
      this.progresoValidacion = 0;
      this.mensajeCarga = 'Carga el nuevo archivo de renovación';
      this.etapaRenovacion = 'cargandoBase'; // Asegurarse de que estamos en la etapa correcta
    } else { // Es el archivo de renovación (o el único archivo en modo 'nueva')
      this.archivo = archivo;
      this.nombreArchivo = archivo.name;
      this.error = '';
      this.reporteActual = null;
      this.mostrarResumen = false;
      this.estadoRevision = 'idle';
      this.progresoValidacion = 0;
      this.mensajeCarga = 'Archivo de renovación cargado, listo para validar/comparar';
    }
    this.arrastrandoArchivo = false;

    // Si es "nueva", el análisis inicia automáticamente.
    // Si es "renovación", el análisis/comparación se activa con el botón "Validar"
    if (this.tipoAccion === 'nueva') {
        this.validar();
    }

    this.cdr.detectChanges();
  }

  // Modificado para aceptar un flag `esArchivoBase`
  private iniciarProgresoSimulado(isBaseFile: boolean): void {
    this.detenerProgresoSimulado(isBaseFile); // Asegurar que no haya otro temporizador corriendo

    this.temporizadorProgreso = setInterval(() => {
      const currentEstaAnalizando = isBaseFile ? (this.estadoRevisionBase === 'analizando') : (this.estadoRevision === 'analizando');

      if (!currentEstaAnalizando) {
        this.detenerProgresoSimulado(isBaseFile);
        return;
      }

      if (isBaseFile) {
        if (this.progresoValidacionBase < 78) {
          this.progresoValidacionBase += 3;
          this.mensajeCargaBase = `Cargando archivo base ${this.progresoBotonBase}%`;
        } else if (this.progresoValidacionBase < 94) {
          this.progresoValidacionBase += 1;
          this.mensajeCargaBase = `Analizando archivo base ${this.progresoBotonBase}%`;
        }
      } else { // No es archivo base (es el archivo nuevo o el único en modo 'nueva')
        if (this.progresoValidacion < 78) {
          this.progresoValidacion += 3;
          this.mensajeCarga = `Cargando datos ${this.progresoBoton}%`;
        } else if (this.progresoValidacion < 94) {
          this.progresoValidacion += 1;
          this.mensajeCarga = `Analizando datos ${this.progresoBoton}%`;
        }
      }
    }, 180);
  }

  // Modificado para aceptar un flag `isBaseFile`, aunque el temporizador es único
  private detenerProgresoSimulado(isBaseFile: boolean): void {
    if (this.temporizadorProgreso) {
      clearInterval(this.temporizadorProgreso);
      this.temporizadorProgreso = null;
    }
  }

  private cancelarSolicitudActiva(): void {
    if (this.solicitudActiva) {
      this.solicitudActiva.unsubscribe();
      this.solicitudActiva = null;
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

  // NUEVO: Resetear todos los estados del componente
  private resetearEstados(): void {
    this.archivo = null;
    this.nombreArchivo = '';
    this.estadoRevision = 'idle';
    this.progresoValidacion = 0;
    this.mensajeCarga = 'Carga un archivo para iniciar el analisis';
    this.error = '';
    this.reporteActual = null;
    this.mostrarResumen = false;
    this.filtroResultados = 'todos';
    this.arrastrandoArchivo = false;

    this.archivoBase = null;
    this.nombreArchivoBase = '';
    this.reporteBase = null;
    this.estadoRevisionBase = 'idle';
    this.progresoValidacionBase = 0;
    this.errorBase = '';
    this.mensajeCargaBase = 'Carga el archivo base para la renovación';
    this.etapaRenovacion = 'cargandoBase';

    this.encabezados = [];
    this.filasConErrores = [];
    this.cancelarSolicitudActiva();
    this.detenerProgresoSimulado(false);
    this.detenerProgresoSimulado(true);
  }


  // Nueva: exportar errores
  descargarErrores(): void {
    console.log('Descargar errores iniciado', {
    reporteActual: this.reporteActual?.nombre_archivo,
    hayErrores: !!this.filasConErrores?.length,
    encabezados: this.encabezados?.length
    });

    if (!this.reporteActual || this.filasConErrores.length === 0) return;
    const payload: any = {
      headers: this.encabezados,
      filas: this.filasConErrores,
      format: this.exportFormato,
      nombre_archivo: this.reporteActual?.nombre_archivo,
    };
    this.validacionSvc.exportarErrores(payload).subscribe((blob: Blob) => {
      const mime = this.exportFormato === 'csv' ? 'text/csv' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const ext = this.exportFormato === 'csv' ? 'csv' : 'xlsx';
      a.download = `${this.reporteActual?.nombre_archivo ?? 'errores'}_errores.${ext}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    });
  }
}
