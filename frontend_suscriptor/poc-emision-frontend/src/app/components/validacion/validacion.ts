import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpEventType, HttpResponse } from '@angular/common/http';
import { NavigationEnd, Router } from '@angular/router';
import { filter } from 'rxjs';
import { ValidacionService, ReporteValidacion, ResultadoValidacion, TipoAccion } from '../../services/validacion';
import { AuthService } from '../../services/auth';

type VistaActiva = 'dashboard' | 'nueva' | 'renovacion';

type EstadoExpediente = 'En proceso' | 'Pendiente' | 'En revision' | 'Completado';

interface Expediente {
  folio: string;
  empresa: string;
  tipo: 'GMM Nueva' | 'GMM Renovacion';
  asegurados: number;
  estado: EstadoExpediente;
  actualizado: string;
}

interface ConfiguracionProceso {
  titulo: string;
  descripcion: string;
  tituloPanel: string;
  subtituloPanel: string;
  columnas: string[];
  nota: string;
}

@Component({
  selector: 'app-validacion',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './validacion.html',
  styleUrl: './validacion.scss',
})
export class ValidacionComponent implements OnInit, OnDestroy {
  tabActiva: TipoAccion = 'nueva';
  menuColapsado = false;
  vistaActiva: VistaActiva = 'dashboard';

  archivoNueva: File | null = null;
  nombreNueva = '';
  archivoRenovacion: File | null = null;
  nombreRenovacion = '';

  cargando = false;
  progresoValidacion = 0;
  mensajeCarga = 'Validar macro';
  error = '';
  reporteActual: ReporteValidacion | null = null;
  filtroResultados: 'todos' | 'error' | 'advertencia' = 'todos';
  arrastrandoArchivo = false;
  private temporizadorProgreso: ReturnType<typeof setInterval> | null = null;

  readonly configuracionProceso: Record<TipoAccion, ConfiguracionProceso> = {
    nueva: {
      titulo: 'Nueva GMM',
      descripcion: 'Carga la macro de censo para iniciar el proceso de emision de una poliza nueva.',
      tituloPanel: 'Proceso de Nueva GMM',
      subtituloPanel: 'Arrastra o selecciona el archivo del censo para iniciar la validacion.',
      columnas: [
        'NOMBRE',
        'APELLIDO_PATERNO',
        'APELLIDO_MATERNO',
        'FECHA_NACIMIENTO',
        'PARENTESCO',
        'CERTIFICADO',
        'FECHA_ANTIGUEDAD',
      ],
      nota: 'La validacion revisa fechas, parentescos, duplicados y certificados con titular obligatorio.',
    },
    renovacion: {
      titulo: 'Renovacion GMM',
      descripcion: 'Carga la macro de renovacion para validar reglas, movimientos y excepciones aplicables.',
      tituloPanel: 'Proceso de Renovacion GMM',
      subtituloPanel: 'Arrastra o selecciona el archivo del censo para iniciar la validacion.',
      columnas: [
        'NOMBRE',
        'APELLIDO_PATERNO',
        'APELLIDO_MATERNO',
        'FECHA_NACIMIENTO',
        'CERTIFICADO',
        'TIPO_MOVIMIENTO',
        'NUMERO_POLIZA',
      ],
      nota: 'La validacion agrega control de tipo de movimiento y permite excepciones de edad solo con endoso y comentario.',
    },
  };

  readonly expedientes: Expediente[] = [
    {
      folio: 'FOL-2026-0031',
      empresa: 'Grupo Industrial Alfa',
      tipo: 'GMM Nueva',
      asegurados: 148,
      estado: 'En proceso',
      actualizado: 'Hoy, 09:40',
    },
    {
      folio: 'FOL-2026-0030',
      empresa: 'Servicios Delta',
      tipo: 'GMM Renovacion',
      asegurados: 96,
      estado: 'Pendiente',
      actualizado: 'Hoy, 08:15',
    },
    {
      folio: 'FOL-2026-0029',
      empresa: 'Corporativo Nativa',
      tipo: 'GMM Nueva',
      asegurados: 204,
      estado: 'En revision',
      actualizado: 'Ayer, 18:20',
    },
    {
      folio: 'FOL-2026-0028',
      empresa: 'Transportes del Bajio',
      tipo: 'GMM Renovacion',
      asegurados: 121,
      estado: 'Completado',
      actualizado: 'Ayer, 16:05',
    },
    {
      folio: 'FOL-2026-0027',
      empresa: 'Manufactura Solis',
      tipo: 'GMM Nueva',
      asegurados: 77,
      estado: 'En proceso',
      actualizado: 'Ayer, 11:32',
    },
  ];

  constructor(
    private validacionSvc: ValidacionService,
    private auth: AuthService,
    private router: Router,
  ) {}

  get username(): string { return this.auth.getUsername(); }

  ngOnInit(): void {
    this.sincronizarVistaConRuta();
    this.router.events
      .pipe(filter((event): event is NavigationEnd => event instanceof NavigationEnd))
      .subscribe(() => this.sincronizarVistaConRuta());
  }

  get expedientesAbiertos(): Expediente[] {
    return this.expedientes.filter((expediente) => expediente.estado !== 'Completado');
  }

  get totalAbiertos(): number {
    return this.expedientesAbiertos.length;
  }

  get abiertosNueva(): number {
    return this.expedientesAbiertos.filter((expediente) => expediente.tipo === 'GMM Nueva').length;
  }

  get abiertosRenovacion(): number {
    return this.expedientesAbiertos.filter((expediente) => expediente.tipo === 'GMM Renovacion').length;
  }

  get esDashboard(): boolean {
    return this.vistaActiva === 'dashboard';
  }

  get tituloProceso(): string {
    return this.configuracionActual.titulo;
  }

  get descripcionProceso(): string {
    return this.configuracionActual.descripcion;
  }

  get configuracionActual(): ConfiguracionProceso {
    return this.configuracionProceso[this.tabActiva];
  }

  get etiquetaArchivo(): string {
    return this.tabActiva === 'nueva' ? this.nombreNueva : this.nombreRenovacion;
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

  toggleMenu(): void {
    this.menuColapsado = !this.menuColapsado;
  }

  irASeccion(vista: VistaActiva): void {
    const destino = vista === 'dashboard'
      ? '/dashboard'
      : vista === 'nueva'
        ? '/gmm/nueva'
        : '/gmm/renovacion';

    this.router.navigate([destino]);
  }

  abrirProceso(tab: TipoAccion): void {
    this.irASeccion(tab);
  }

  verExpediente(expediente: Expediente): void {
    this.irASeccion(expediente.tipo === 'GMM Nueva' ? 'nueva' : 'renovacion');
  }

  estadoClase(estado: EstadoExpediente): string {
    return estado
      .toLowerCase()
      .replace(/\s+/g, '-');
  }

  setTab(tab: TipoAccion): void {
    this.tabActiva = tab;
    this.error = '';
    this.reporteActual = null;
    this.filtroResultados = 'todos';
    this.arrastrandoArchivo = false;
  }

  onArchivoNueva(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files?.length) {
      this.archivoNueva = input.files[0];
      this.nombreNueva = input.files[0].name;
      this.error = '';
      this.reporteActual = null;
      this.arrastrandoArchivo = false;
    }
  }

  onArchivoRenovacion(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files?.length) {
      this.archivoRenovacion = input.files[0];
      this.nombreRenovacion = input.files[0].name;
      this.error = '';
      this.reporteActual = null;
      this.arrastrandoArchivo = false;
    }
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    this.arrastrandoArchivo = true;
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    this.arrastrandoArchivo = false;
  }

  onDropArchivo(event: DragEvent): void {
    event.preventDefault();
    this.arrastrandoArchivo = false;

    const archivo = event.dataTransfer?.files?.[0];
    if (!archivo) {
      return;
    }

    this.asignarArchivo(archivo, this.tabActiva);
  }

  get archivoActivo(): File | null {
    return this.tabActiva === 'nueva' ? this.archivoNueva : this.archivoRenovacion;
  }

  get progresoBoton(): number {
    return Math.max(0, Math.min(100, this.progresoValidacion));
  }

  botonDeshabilitado(tab: TipoAccion): boolean {
    const archivo = tab === 'nueva' ? this.archivoNueva : this.archivoRenovacion;
    return !archivo || this.cargando || this.tabActiva !== tab;
  }

  etiquetaBoton(tab: TipoAccion): string {
    if (!this.cargando || this.tabActiva !== tab) {
      return 'Validar macro';
    }

    return this.mensajeCarga;
  }

  ngOnDestroy(): void {
    this.detenerProgresoSimulado();
  }

  validar(): void {
    if (!this.archivoActivo) return;
    this.cargando = true;
    this.error = '';
    this.reporteActual = null;
    this.filtroResultados = 'todos';
    this.progresoValidacion = 8;
    this.mensajeCarga = 'Cargando archivo 8%';
    this.iniciarProgresoSimulado();

    this.validacionSvc.validarMacro(this.archivoActivo, this.tabActiva, 'GMM').subscribe({
      next: (evento) => {
        if (evento.type === HttpEventType.UploadProgress) {
          const total = evento.total ?? evento.loaded;
          const porcentajeCarga = total > 0
            ? Math.round((evento.loaded / total) * 70)
            : Math.min(70, this.progresoValidacion + 5);

          this.progresoValidacion = Math.max(this.progresoValidacion, porcentajeCarga);
          this.mensajeCarga = `Cargando archivo ${this.progresoBoton}%`;
          return;
        }

        if (evento.type === HttpEventType.Response) {
          this.finalizarCarga();
          const reporte = (evento as HttpResponse<ReporteValidacion>).body;
          if (!reporte) {
            this.error = 'La respuesta del servidor no incluye el reporte de validacion.';
            return;
          }

          this.reporteActual = reporte;
        }
      },
      error: (err: { error?: { detail?: string } }) => {
        this.finalizarCarga();
        this.error = err?.error?.detail ?? 'Error al procesar la macro. Verifica el archivo e intenta de nuevo.';
      },
    });
  }

  private iniciarProgresoSimulado(): void {
    this.detenerProgresoSimulado();

    this.temporizadorProgreso = setInterval(() => {
      if (!this.cargando) {
        this.detenerProgresoSimulado();
        return;
      }

      if (this.progresoValidacion < 70) {
        this.progresoValidacion += 4;
        this.mensajeCarga = `Cargando archivo ${this.progresoBoton}%`;
        return;
      }

      if (this.progresoValidacion < 94) {
        this.progresoValidacion += 1;
        this.mensajeCarga = `Validando reglas ${this.progresoBoton}%`;
      }
    }, 180);
  }

  private detenerProgresoSimulado(): void {
    if (this.temporizadorProgreso) {
      clearInterval(this.temporizadorProgreso);
      this.temporizadorProgreso = null;
    }
  }

  private finalizarCarga(): void {
    this.detenerProgresoSimulado();
    this.progresoValidacion = 100;
    this.mensajeCarga = 'Validacion completada';
    this.cargando = false;
  }

  setFiltroResultados(filtro: 'todos' | 'error' | 'advertencia'): void {
    this.filtroResultados = filtro;
  }

  obtenerClaseResultado(tipo: ResultadoValidacion['tipo']): string {
    return tipo === 'advertencia' ? 'advertencia' : 'error';
  }

  private sincronizarVistaConRuta(): void {
    const ruta = this.router.url.toLowerCase();

    if (ruta.includes('/gmm/nueva')) {
      this.vistaActiva = 'nueva';
      if (this.tabActiva !== 'nueva') {
        this.setTab('nueva');
      }
      return;
    }

    if (ruta.includes('/gmm/renovacion')) {
      this.vistaActiva = 'renovacion';
      if (this.tabActiva !== 'renovacion') {
        this.setTab('renovacion');
      }
      return;
    }

    this.vistaActiva = 'dashboard';
  }

  private asignarArchivo(archivo: File, tipo: TipoAccion): void {
    this.error = '';
    this.reporteActual = null;

    if (tipo === 'nueva') {
      this.archivoNueva = archivo;
      this.nombreNueva = archivo.name;
      return;
    }

    this.archivoRenovacion = archivo;
    this.nombreRenovacion = archivo.name;
  }

  logout(): void {
    this.auth.logout();
    this.router.navigate(['/login']);
  }
}
