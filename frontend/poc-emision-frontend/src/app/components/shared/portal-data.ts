import { TipoAccion } from '../../services/validacion';

export type SeccionPortal = 'dashboard' | 'nueva' | 'renovacion';

export interface ConfiguracionProceso {
  titulo: string;
  descripcion: string;
  tituloPanel: string;
  subtituloPanel: string;
  columnas: string[];
  nota: string;
  subtipo: 'GMM Nueva' | 'GMM Renovacion';
}

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