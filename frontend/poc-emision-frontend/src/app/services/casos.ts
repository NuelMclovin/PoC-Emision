import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ReporteValidacion, TipoAccion, TipoProducto } from './validacion';

export type EstadoCaso = 'Pendiente' | 'En revisión' | 'Observado' | 'Aprobado' | 'Rechazado';

export interface DocumentoInfo {
  nombre: string;
  tipo: 'macro' | 'reporte' | 'anexo';
  tamano_bytes: number;
  subido_en: string;
  subido_por?: string | null;
}

export interface CasoResumen {
  folio: string;
  empresa: string;
  tipo_accion: TipoAccion;
  tipo_producto: TipoProducto;
  estado: EstadoCaso;
  creado_por: string;
  asignado_a: string | null;
  fecha_creacion: string;
  fecha_actualizacion: string;
  total_registros: number;
  total_titulares: number;
  total_dependientes: number;
  total_errores: number;
  total_advertencias: number;
  es_valida: boolean;
  comentario_suscriptor: string;
  nombre_archivo_macro: string;
}

export interface CasoDetalle extends CasoResumen {
  reporte: ReporteValidacion | null;
  documentos: DocumentoInfo[];
}

export interface FiltrosCasos {
  estado?: EstadoCaso;
  tipo_accion?: TipoAccion;
  tipo_producto?: TipoProducto;
  creado_por?: string;
  asignado_a?: string;
}

export interface CasoActualizar {
  estado?: EstadoCaso;
  asignado_a?: string;
  comentario_suscriptor?: string;
}

/** Estados en los que el expediente ya no requiere acción (cerrado). */
export const ESTADOS_CERRADOS: EstadoCaso[] = ['Aprobado', 'Rechazado'];

/** Normaliza un estado a una clase CSS estable (sin acentos ni espacios). */
export function estadoClase(estado: EstadoCaso | string): string {
  return estado
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLowerCase()
    .replace(/\s+/g, '-');
}

@Injectable({ providedIn: 'root' })
export class CasosService {
  // URL relativa → pasa por el proxy de Angular (proxy.conf.json → localhost:8000)
  private readonly API = '/api/v1/casos';

  constructor(private http: HttpClient) {}

  crearCaso(
    archivo: File,
    empresa: string,
    tipoAccion: TipoAccion,
    tipoProducto: TipoProducto,
  ): Observable<CasoDetalle> {
    const form = new FormData();
    form.append('archivo', archivo, archivo.name);
    form.append('empresa', empresa);
    form.append('tipo_accion', tipoAccion);
    form.append('tipo_producto', tipoProducto);
    return this.http.post<CasoDetalle>(this.API, form);
  }

  listarCasos(filtros: FiltrosCasos = {}): Observable<CasoResumen[]> {
    let params: Record<string, string> = {};
    Object.entries(filtros).forEach(([clave, valor]) => {
      if (valor) {
        params[clave] = valor;
      }
    });
    return this.http.get<CasoResumen[]>(this.API, { params });
  }

  obtenerCaso(folio: string): Observable<CasoDetalle> {
    return this.http.get<CasoDetalle>(`${this.API}/${encodeURIComponent(folio)}`);
  }

  actualizarCaso(folio: string, cambios: CasoActualizar): Observable<CasoDetalle> {
    return this.http.patch<CasoDetalle>(`${this.API}/${encodeURIComponent(folio)}`, cambios);
  }

  listarDocumentos(folio: string): Observable<DocumentoInfo[]> {
    return this.http.get<DocumentoInfo[]>(`${this.API}/${encodeURIComponent(folio)}/documentos`);
  }

  subirDocumento(folio: string, archivo: File): Observable<DocumentoInfo> {
    const form = new FormData();
    form.append('archivo', archivo, archivo.name);
    return this.http.post<DocumentoInfo>(`${this.API}/${encodeURIComponent(folio)}/documentos`, form);
  }

  descargarDocumento(folio: string, nombre: string): Observable<Blob> {
    return this.http.get(`${this.API}/${encodeURIComponent(folio)}/documentos/${encodeURIComponent(nombre)}`, {
      responseType: 'blob',
    });
  }
}