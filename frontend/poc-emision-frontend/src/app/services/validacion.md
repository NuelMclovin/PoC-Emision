import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent } from '@angular/common/http';
import { Observable } from 'rxjs';

export type TipoAccion = 'nueva' | 'renovacion';
export type TipoProducto = 'GMM' | 'AP';

export interface ResultadoValidacion {
  tipo: 'error' | 'advertencia' | 'info';
  categoria: string;
  mensaje: string;
  fila: number | null;
  columna: string | null;
  valor: string | null;
}

export interface ResumenValidacion {
  total_registros: number;
  total_titulares: number;
  total_dependientes: number;
  total_errores: number;
  total_advertencias: number;
  es_valida: boolean;
}

export interface ReporteValidacion {
  nombre_archivo: string;
  resumen: ResumenValidacion;
  resultados: ResultadoValidacion[];
}


@Injectable({ providedIn: 'root' })
export class ValidacionService {
  // URL relativa → pasa por el proxy de Angular (proxy.conf.json → localhost:8000)
  private readonly API = '/api/v1/validacion';

  constructor(private http: HttpClient) {}

  validarMacro(
    archivo: File,
    tipoAccion: TipoAccion,
    tipoProducto: TipoProducto,
  ): Observable<HttpEvent<ReporteValidacion>> {
    const form = new FormData();
    form.append('archivo', archivo, archivo.name);
    form.append('tipo_accion', tipoAccion);
    form.append('tipo_producto', tipoProducto);
    return this.http.post<ReporteValidacion>(`${this.API}/macro`, form, {
      observe: 'events',
      reportProgress: true,
    });
  }

  /**
   * Solicita al backend la descarga de un archivo con los registros del censo que contienen errores.
   * @param archivo El archivo original del censo.
   * @param tipoAccion Tipo de acción (nueva/renovacion).
   * @param tipoProducto Tipo de producto (GMM/AP).
   * @param filasConError Un array con los números de fila (1-based) que contienen errores.
   * @param formato El formato de salida deseado (csv/excel).
   * @returns Un Observable que emite un Blob con el contenido del archivo.
   */
  descargarResultados(
    archivo: File,
    tipoAccion: TipoAccion,
    tipoProducto: TipoProducto,
    filasConError: number[],
    formato: 'csv' | 'excel'
  ): Observable<Blob> {
    const form = new FormData();
    form.append('archivo', archivo, archivo.name);
    form.append('tipo_accion', tipoAccion);
    form.append('tipo_producto', tipoProducto);
    form.append('filas_con_error', JSON.stringify(filasConError)); // Enviar como JSON string
    form.append('formato', formato);

    return this.http.post(`${this.API}/descargar-errores`, form, {
      responseType: 'blob' // Es crucial para recibir el archivo como un Blob
    });
  }
}


