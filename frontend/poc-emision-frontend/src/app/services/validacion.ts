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
}
