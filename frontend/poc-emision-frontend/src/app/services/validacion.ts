import { HttpClient, HttpEventType, HttpResponse } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Injectable } from '@angular/core';

// Tipos de dominio expuestos al frontend
export type TipoAccion = 'nueva' | 'renovacion';

export type TipoProducto = 'GMM' | 'AP';


// Modelo de resumen de validación
export interface ResumenValidacion {
  total_registros: number;
  total_titulares: number;
  total_dependientes: number;
  total_errores: number;
  total_advertencias: number;
  es_valida: boolean;
}

// Modelo de un resultado de validación
export interface ResultadoValidacion {
  tipo: 'error' | 'advertencia' | 'info';
  categoria: string;
  mensaje: string;
  fila?: number;
  columna?: string;
  columnas_afectadas?: string[];
  valor?: string;
  tipo_movimiento?: 'Cambio' | 'Alta' | 'Baja' | 'Vigente';
  detalle?: string;
}

// Modelo de reporte completo
export interface ReporteValidacion {
  nombre_archivo: string;
  resumen: ResumenValidacion;
  resultados: ResultadoValidacion[];
  // Campos opcionales para exportar (no romper compatibilidad)
  encabezados?: string[];
  filas_con_errores?: any[];
  offset_filas?: number;
}

@Injectable({ providedIn: 'root' })
export class ValidacionService {
  constructor(private http: HttpClient) {}

  // Método existente de validación (mantén funcionalidad anterior)
  validarMacro(archivo: File, tipoAccion: TipoAccion, tipoProducto: 'GMM' | 'AP'): Observable<any> {
    const formData = new FormData();
    formData.append('archivo', archivo, archivo.name);
    formData.append('tipo_accion', tipoAccion);
    formData.append('tipo_producto', tipoProducto);
    const url = '/api/v1/validacion/macro';
    return this.http.post(url, formData, {
      observe: 'events',
      reportProgress: true
    });
  }

  validarBaseRenovacion(archivo: File): Observable<any> {
    const formData = new FormData();
    formData.append('archivo', archivo, archivo.name);
    return this.http.post('/api/v1/validacion/renovacion/base', formData, {
      observe: 'events',
      reportProgress: true
    });
  }


  // NUEVO MÉTODO: Validar y comparar macro para renovación
  validarYCompararMacro(
    archivoNuevo: File,
    archivoBase: File,
    tipoAccion: TipoAccion, // Siempre será 'renovacion'
    tipoProducto: 'GMM' | 'AP'
  ): Observable<any> {
    const formData = new FormData();
    formData.append('archivo_nuevo', archivoNuevo, archivoNuevo.name);
    formData.append('archivo_base', archivoBase, archivoBase.name);
    formData.append('tipo_accion', tipoAccion);
    formData.append('tipo_producto', tipoProducto);
    // Usaremos un nuevo endpoint en el backend para esto
    const url = '/api/v1/validacion/renovacion-con-base';
    return this.http.post(url, formData, {
      observe: 'events',
      reportProgress: true
    });
  }


  // Nueva: exportar errores
  exportarErrores(payload: { headers: string[]; filas: any[]; format: 'csv' | 'xlsx'; nombre_archivo?: string }): Observable<Blob> {
    // Forzar Blob como respuesta
    return this.http.post('/api/v1/validacion/export-errores', payload, {
      responseType: 'blob' as 'json'
    }) as Observable<Blob>; // esta línea asegura que el tipo de respuesta sea Blob, aunque TypeScript lo infiera como 'json' por defecto
  }
}
