import { TipoAccion } from '../../services/validacion';

export type SeccionPortal = 'dashboard' | 'nueva' | 'renovacion';
export type EstadoExpediente = 'En proceso' | 'Pendiente' | 'En revision' | 'Completado';

export interface Expediente {
  folio: string;
  empresa: string;
  tipo: 'GMM Nueva' | 'GMM Renovacion';
  asegurados: number;
  estado: EstadoExpediente;
  actualizado: string;
}

export interface ConfiguracionProceso {
  titulo: string;
  descripcion: string;
  tituloPanel: string;
  subtituloPanel: string;
  columnas: string[];
  nota: string;
  subtipo: 'GMM Nueva' | 'GMM Renovacion';
}

export const EXPEDIENTES_MOCK: Expediente[] = [
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

export const CONFIGURACION_PROCESO: Record<TipoAccion, ConfiguracionProceso> = {
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
    subtipo: 'GMM Nueva',
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
    subtipo: 'GMM Renovacion',
  },
};

export function estadoClase(estado: EstadoExpediente): string {
  return estado.toLowerCase().replace(/\s+/g, '-');
}