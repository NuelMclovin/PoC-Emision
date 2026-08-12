# PoC Proceso de Emision

## 1) Proposito del proyecto
Este repositorio implementa una prueba de concepto para validar archivos de censo (Excel/CSV) usados en emision de polizas GMM colectivas, con dos frentes:

- Backend API para autenticacion mock, lectura de layouts y validacion por reglas de negocio.
- Frontend Angular para login, seleccion de proceso (nueva/renovacion), carga de archivo y visualizacion del reporte.

Objetivo principal:
- Detectar errores y advertencias de datos antes de continuar con la emision.
- Entregar un resumen legible por negocio con trazabilidad por fila/columna.

## 2) Arquitectura general
Componentes:

- API FastAPI en backend/app/main.py
- Configuracion central en backend/app/config.py
- Reglas de negocio en backend/app/core/reglas_negocio.py
- Lectura de macros/layouts en backend/app/services/macro_reader.py
- Orquestacion de validacion en backend/app/services/validator.py
- Endpoints en backend/app/routers/auth_router.py y backend/app/routers/validacion_router.py
- App Angular standalone en frontend/poc-emision-frontend/src/app
- Orquestacion Docker en docker-compose.yml

Flujo alto nivel:
1. Usuario inicia sesion en frontend.
2. Selecciona tipo de proceso (nueva o renovacion).
3. Carga archivo macro/layout.
4. Frontend envia archivo al backend.
5. Backend lee estructura, aplica reglas RN y regresa resultados.
6. Frontend muestra KPIs, tabla de hallazgos y filtros por severidad.

## 3) Estructura de carpetas y que hace cada una

- backend: API, logica de negocio, servicios y pruebas unitarias.
- frontend: aplicacion Angular de interfaz.
- Layout Polizas: archivos de layout y ejemplos de prueba.
- docker-compose.yml: levanta backend y frontend en contenedores.
- .gitignore: exclusion de temporales, entornos y secretos.

### 3.1 Backend
- backend/app: codigo fuente principal.
- backend/app/core: reglas de negocio por campo/dato.
- backend/app/models: modelos de entrada/salida de validacion.
- backend/app/routers: endpoints HTTP.
- backend/app/services: lectura de archivo y validacion.
- backend/app/utils: utilidades comunes (logger).
- backend/tests: pruebas del backend.
- backend/tmp/uploads: almacenamiento temporal de archivos.

### 3.2 Frontend
- frontend/poc-emision-frontend/src/app: app Angular.
- frontend/poc-emision-frontend/src/app/components: UI por pantallas/componentes.
- frontend/poc-emision-frontend/src/app/services: clientes HTTP y estado de sesion.
- frontend/poc-emision-frontend/src/app/guards: proteccion de rutas autenticadas.
- frontend/poc-emision-frontend/src/app/interceptors: interceptor de auth.
- frontend/poc-emision-frontend/proxy.conf.json: proxy hacia backend en desarrollo.

## 4) Descripcion por archivo relevante y metodos clave

## 4.1 Backend

- backend/app/main.py
  - Que hace: crea y configura la app FastAPI, CORS, routers y healthcheck.
  - Metodos clave: create_app, endpoint health.

- backend/app/config.py
  - Que hace: centraliza settings (origenes CORS, upload dir, auth flags, integracion externa).
  - Metodos clave: parseo de settings, ensure_upload_dir, get_settings.

- backend/app/routers/auth_router.py
  - Que hace: login/logout y validacion de token en modo mock.
  - Metodos clave: endpoints de autenticacion.

- backend/app/routers/validacion_router.py
  - Que hace: endpoint de validacion de macro; controla tipo/tamano de archivo, invoca lectura y validador.
  - Metodos clave: validar_macro_endpoint.

- backend/app/services/macro_reader.py
  - Que hace: lectura de XLS/XLSX/XLSM/CSV, normalizacion de columnas y calculo de offset real de fila.
  - Metodos clave: leer_macro, _leer_excel, _leer_csv, normalizacion de encabezados.

- backend/app/core/reglas_negocio.py
  - Que hace: define reglas RN-00 a RN-09 y seleccion por tipo de movimiento.
  - Metodos clave:
    - obtener_reglas
    - regla_fecha_nacimiento
    - regla_edad_limite
    - regla_tipo_movimiento
    - utilidades de parseo/normalizacion de fecha y validaciones de campos.

- backend/app/services/validator.py
  - Que hace: orquesta ejecucion de reglas por registro y arma el reporte final.
  - Metodos clave: validar_macro (resumen, conteos y lista de hallazgos).

- backend/app/models/macro_models.py
  - Que hace: modelos de respuesta para resultados, resumen y estructura de reporte.

- backend/app/utils/logger.py
  - Que hace: configuracion de logging reutilizable para backend.

- backend/tests/test_validacion.py
  - Que hace: pruebas de comportamiento del endpoint/reglas de validacion.

## 4.2 Frontend

- frontend/poc-emision-frontend/src/app/app.routes.ts
  - Que hace: define rutas principales (login, dashboard, nueva GMM, renovacion, reporte).

- frontend/poc-emision-frontend/src/app/app.config.ts
  - Que hace: configuracion global de providers (router, http, interceptor).

- frontend/poc-emision-frontend/src/app/app.ts
  - Que hace: componente raiz y render de navegacion principal.

- frontend/poc-emision-frontend/src/app/components/login/login.ts
  - Que hace: captura de credenciales y sesion.

- frontend/poc-emision-frontend/src/app/components/dashboard/dashboard.ts
  - Que hace: vista de entrada al portal con accesos a procesos.

- frontend/poc-emision-frontend/src/app/components/portal-shell/portal-shell.ts
  - Que hace: shell reusable del portal (encabezado, contexto de seccion, contenedor de contenido).

- frontend/poc-emision-frontend/src/app/components/gmm-proceso/gmm-proceso.ts
  - Que hace: flujo principal de carga y validacion.
  - Metodos clave:
    - manejo de archivo drag-drop/selector
    - validar
    - iniciarProgresoSimulado
    - cancelarSolicitudActiva
    - filtros de resultados y resumen inline.

- frontend/poc-emision-frontend/src/app/components/gmm-proceso/gmm-proceso.html
  - Que hace: UI del proceso, estado de carga, KPIs y tabla de resultados embebida.

- frontend/poc-emision-frontend/src/app/components/gmm-proceso/gmm-proceso.scss
  - Que hace: estilos del flujo, estados visuales y microanimaciones.

- frontend/poc-emision-frontend/src/app/components/nueva-gmm/nueva-gmm.ts
  - Que hace: wrapper para proceso tipo nueva.

- frontend/poc-emision-frontend/src/app/components/renovacion-gmm/renovacion-gmm.ts
  - Que hace: wrapper para proceso tipo renovacion.

- frontend/poc-emision-frontend/src/app/components/validacion/validacion.ts
  - Que hace: componente legacy del flujo anterior; ya no es el camino principal.

- frontend/poc-emision-frontend/src/app/components/reporte/reporte.ts
  - Que hace: vista legacy de reporte via sessionStorage.

- frontend/poc-emision-frontend/src/app/services/auth.ts
  - Que hace: autenticacion, estado de sesion y utilidades de token.

- frontend/poc-emision-frontend/src/app/services/validacion.ts
  - Que hace: cliente HTTP para enviar macro y recibir reporte de validacion.

- frontend/poc-emision-frontend/src/app/guards/auth-guard.ts
  - Que hace: bloquea navegacion a rutas protegidas sin sesion.

- frontend/poc-emision-frontend/src/app/interceptors/auth.interceptor.ts
  - Que hace: agrega cabeceras de autenticacion a peticiones HTTP.

## 5) Endpoints y contrato funcional

Autenticacion:
- Endpoint en backend/app/routers/auth_router.py
- Uso: login/logout/validacion de sesion mock para habilitar navegacion frontend.

Validacion:
- Endpoint en backend/app/routers/validacion_router.py
- Entrada: archivo de macro/layout.
- Salida:
  - Resumen: total registros, titulares, dependientes, errores, advertencias, bandera de validez.
  - Detalle: lista de hallazgos con tipo, categoria, mensaje, fila, columna y valor.

Health:
- Endpoint en backend/app/main.py
- Uso: verificacion rapida de disponibilidad de API.

## 6) Ejecucion del proyecto

Con Docker:
- Usar docker-compose.yml
- Levanta backend en puerto 8000 y frontend en puerto 4200.

Local:
- Backend:
  - Dependencias y scripts en backend/pyproject.toml
- Frontend:
  - Dependencias y scripts en frontend/poc-emision-frontend/package.json
  - Proxy dev en frontend/poc-emision-frontend/proxy.conf.json

## 7) Datos de prueba y layouts
Carpeta Layout Polizas:
- Layout Para Emision de Poliza Nueva.xlsm
- Layout Renovacion Poliza.xlsm
- Archivos de prueba para escenarios validos y con errores (xlsx/xlsm)

Uso recomendado:
- Probar ambos procesos (nueva y renovacion).
- Comparar el resultado esperado de reglas RN con el detalle devuelto por la API.

## 8) Estado actual y notas de mantenimiento

Estado actual:
- Flujo principal de validacion consolidado en componente gmm-proceso.
- Resumen y tabla de hallazgos se muestran en la misma pantalla.
- Manejo de estados de carga y cancelacion robusto.

Coexistencia legacy:
- Siguen presentes componentes legacy frontend/poc-emision-frontend/src/app/components/validacion/validacion.ts y frontend/poc-emision-frontend/src/app/components/reporte/reporte.ts, utiles para compatibilidad o referencia historica.

Riesgos/deuda tecnica:
- Specs basicos en frontend validan creacion de componentes/servicios, pero falta cobertura funcional profunda.
- Hay plantilla inicial de Angular todavia visible en frontend/poc-emision-frontend/src/app/app.html, conviene limpiarla para evitar ruido.
- Definir estrategia para retirar rutas/componentes legacy cuando se confirme adopcion total del flujo nuevo.

## 9) Recomendaciones de siguiente iteracion
1. Aumentar pruebas de integracion backend para reglas RN por tipo de movimiento.
2. Agregar pruebas frontend del flujo completo: carga, estado, respuesta y filtros.
3. Plan de deprecacion para componentes legacy y rutas antiguas.
4. Incorporar documentacion de contrato de API en formato OpenAPI/coleccion de pruebas.
