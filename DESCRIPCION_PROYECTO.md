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

- **backend/app/main.py**
  - **Que hace:** Crea y configura la aplicación FastAPI. Es el punto de entrada principal del backend.
  - **Metodos clave:**
    - `create_app()`: Inicializa la aplicación FastAPI, configura el título, la versión y la descripción, añade el middleware CORS (utilizando los orígenes permitidos definidos en `config.py`), e incluye los routers de autenticación, validación y casos. También asegura la existencia de los directorios de carga y datos.
    - `/health` endpoint: Proporciona un chequeo rápido de disponibilidad de la API.

- **backend/app/config.py**
  - **Que hace:** Centraliza todas las configuraciones y ajustes de la aplicación, cargándolos desde variables de entorno o un archivo `.env`.
  - **Metodos clave:**
    - `Settings`: Clase Pydantic para definir y validar las variables de configuración como el entorno, nivel de logging, orígenes CORS permitidos (con un validador para parsear listas CSV), directorios de carga y datos, configuración de autenticación mock, y credenciales para servicios externos como Azure Document Intelligence y Azure Service Principal.
    - `ensure_upload_dir()`: Crea el directorio de carga si no existe.
    - `ensure_data_dirs()`: Crea los directorios para el almacenamiento local de casos y documentos.
    - `get_settings()`: Función que usa `lru_cache` para obtener una instancia única y eficiente de la configuración.

- **backend/app/routers/validacion_router.py**
  - **Que hace:** Define el endpoint principal para la validación de macros de emisión.
  - **Metodos clave:**
    - `validar_macro_endpoint`: Maneja las solicitudes POST al path `/api/v1/validacion/macro`. Recibe un archivo (macro de emisión), el tipo de acción (`nueva` o `renovacion`) y el tipo de producto (`GMM` o `AP`). Realiza validaciones de extensión y tamaño del archivo, invoca a `leer_macro` para procesar el archivo y a `validar_macro` para aplicar las reglas de negocio, devolviendo un `ReporteValidacion` detallado.

-   **backend/app/services/macro_reader.py**
    -   **Que hace:** Se encarga de la lectura, normalización y pre-procesamiento de los archivos macro (Excel o CSV) que se suben para validación. Determina el formato del archivo y el layout de AXA a utilizar (GMM/AP, nueva/renovación) para extraer los datos correctamente.
    -   **Metodos clave:**
        -   `leer_macro()`: Función principal que orquesta la lectura. Detecta la extensión del archivo (`.xlsx`, `.xls`, `.xlsm`, `.csv`), invoca el método de lectura apropiado (`_leer_excel` o `_leer_csv`), y devuelve un `DataFrame` de Pandas con los datos y el `offset` de filas real para la numeración en el Excel original.
        -   `_leer_excel()`: Lee archivos Excel, identificando la hoja y la fila de encabezado según el `LAYOUT_MAP` predefinido, y manejando las filas a saltar.
        -   `_leer_csv()`: Lee archivos CSV, intentando múltiples codificaciones para asegurar la compatibilidad.
        -   `_normalizar_columnas()`: Estandariza los nombres de las columnas del `DataFrame` (mayúsculas, sin acentos, espacios por guiones bajos) para facilitar el procesamiento por las reglas de negocio.

-   **backend/app/core/reglas_negocio.py**
    -   **Que hace:** Contiene la implementación de todas las reglas de negocio (RN-00 a RN-09) que se aplican a las macros de emisión. Incluye funciones auxiliares para el manejo de fechas, cálculo de edades y la generación de resultados de validación.
    -   **Metodos clave:**
        -   `_calcular_fila_real()`: Convierte el índice de fila del `DataFrame` a la fila real en el archivo Excel original, considerando el `offset` de filas.
        -   `_parse_fecha()`, `_obtener_razon_rechazo_fecha()`, `_edad()`: Funciones utilitarias para parsear y validar fechas, así como calcular la edad de una persona.
        -   `regla_columnas_requeridas()` (RN-00): Verifica la presencia de columnas obligatorias.
        -   `regla_duplicados_persona()` (RN-01): Detecta registros duplicados de personas.
        -   `regla_fecha_nacimiento()` (RN-02): Valida la fecha de nacimiento (formato, no futura, límites de edad).
        -   `regla_antiguedad_vs_nacimiento()` (RN-03): Asegura que la fecha de antigüedad no sea anterior a la de nacimiento.
        -   `regla_certificado_sin_titular()` (RN-04): Verifica que cada certificado tenga un titular.
        -   `regla_conyuge_unico()` (RN-05): Limita a un cónyuge por certificado.
        -   `regla_titular_unico()` (RN-06): Limita a un titular por certificado.
        -   `regla_edad_limite()` (RN-07, RN-08): Aplica las reglas de edad máxima para titulares, cónyuges y beneficiarios, incluyendo excepciones para renovaciones con endoso.
        -   `regla_tipo_movimiento()` (RN-09): Valida los valores del campo `TIPO_MOVIMIENTO` en macros de renovación.
        -   `obtener_reglas()`: Función principal que, en base al `tipo_accion` y `tipo_producto`, devuelve una lista de las funciones de reglas de negocio aplicables.

-   **backend/app/services/validator.py**
    -   **Que hace:** Actúa como el orquestador principal del proceso de validación. Recibe el `DataFrame` pre-procesado y aplica secuencialmente las reglas de negocio definidas en `reglas_negocio.py` para generar un reporte completo.
    -   **Metodos clave:**
        -   `validar_macro()`: Toma el `DataFrame`, el nombre del archivo, el tipo de acción y producto, y el `fila_offset`. Invoca `obtener_reglas` para obtener las reglas pertinentes, las ejecuta, recopila todos los `ResultadoValidacion` y construye un `ReporteValidacion` final que incluye un resumen y la lista detallada de hallazgos.

-   **backend/app/models/macro_models.py**
    -   **Que hace:** Define los modelos de datos (utilizando Pydantic) para las estructuras de información utilizadas en el proceso de validación y en las respuestas de la API. Incluye enumeraciones para conceptos clave del dominio.
    -   **Metodos clave:**
        -   `Parentesco`, `Genero`, `TipoError`: Enumeraciones que estandarizan los valores para parentescos, géneros y tipos de hallazgos de validación.
        -   `ResultadoValidacion`: Modelo para representar un hallazgo individual de validación, especificando tipo (error/advertencia), categoría, mensaje, fila, columna y valor afectado.
        -   `ResumenValidacion`: Modelo que encapsula un resumen estadístico del proceso de validación (total de registros, titulares, dependientes, errores, advertencias, y si la macro es válida).
        -   `ReporteValidacion`: Modelo de respuesta completa para la validación, que agrupa el nombre del archivo, el resumen y la lista de todos los `ResultadoValidacion`.
        -   `LoginRequest`, `TokenResponse`: Modelos para la gestión de autenticación mock (solicitud de login y respuesta de token).

-   **backend/app/utils/logger.py**
    -   **Que hace:** Provee una configuración de logging estándar y reutilizable para todo el backend del proyecto.
    -   **Metodos clave:**
        -   `get_logger()`: Devuelve una instancia de `logging.Logger` configurada. Asegura que el logger se configure una sola vez (gracias a `@lru_cache`) con un `StreamHandler` que envía los logs a la salida estándar (`sys.stdout`) y un formato predefinido, estableciendo el nivel de logging a `DEBUG`.


-   **backend/tests/test_validacion.py**
    -   **Que hace:** Contiene las pruebas unitarias para las reglas de negocio implementadas en el backend. Utiliza el framework `pytest` y `pandas` para simular escenarios y verificar el comportamiento de cada regla de validación.
    -   **Metodos clave:**
        -   `_fila()`, `_df()`: Funciones auxiliares para crear datos de prueba de manera sencilla.
        -   `test_columnas_requeridas_ok()`, `test_columnas_requeridas_falta_certificado()`, etc.: Funciones de prueba que validan las diferentes reglas de negocio (RN-00 a RN-08) en diversos escenarios (casos válidos, con errores, con advertencias, etc.).





## 4.2 Frontend

- **frontend/poc-emision-frontend/src/app/app.routes.ts**
  - **Que hace:** Configura las rutas principales de navegación de la aplicación Angular.
  - **Metodos clave:**
    - `routes`: Un array de objetos que define las diferentes rutas, incluyendo `login`, `dashboard`, procesos de GMM (`nueva` y `renovacion`), `reporte` y `expediente/:folio`. Utiliza `authGuard` para proteger las rutas que requieren autenticación y carga perezosa (`loadComponent`) para optimizar el rendimiento.

- **frontend/poc-emision-frontend/src/app/components/gmm-proceso/gmm-proceso.ts**
  - **Que hace:** Es el componente central que orquesta el flujo de carga, validación y visualización de resultados para los procesos de GMM (nueva o renovación).
  - **Metodos clave:**
    - `validar()`: Inicia el proceso de validación, enviando el archivo cargado al backend y manejando la respuesta, incluyendo el progreso de carga y análisis.
    - `onArchivoSeleccionado()`, `onDragOver()`, `onDragLeave()`, `onDropArchivo()`: Métodos para manejar la carga de archivos, tanto por selección como por arrastrar y soltar.
    - `reiniciarEstado()`: Restablece el componente a su estado inicial, descartando el análisis actual.
    - `iniciarProgresoSimulado()`, `detenerProgresoSimulado()`: Controlan la simulación de la barra de progreso durante la carga y el análisis.
    - `cancelarSolicitudActiva()`: Cancela cualquier solicitud HTTP de validación que esté en curso.
    - `setFiltroResultados()`: Permite filtrar los resultados del reporte (todos, errores, advertencias).
    - `enviarASuscripcion()`: Gestiona el envío del expediente validado a un servicio de suscripción, creando un caso.
    - Propiedades computadas: `estaAnalizando`, `estaFinalizado`, `totalErrores`, `totalAdvertencias`, `resumenHallazgos`, entre otras, para controlar la lógica de visualización y el estado de la interfaz.

-   **frontend/poc-emision-frontend/src/app/services/auth.ts**
    -   **Que hace:** Gestiona la autenticación del usuario en el frontend. Se encarga de realizar el login, guardar y recuperar el token de autenticación y la información del usuario (nombre de usuario, rol, nombre completo) en el `localStorage` del navegador.
    -   **Metodos clave:**
        -   `login()`: Envía las credenciales al backend y, si son válidas, almacena los datos de la sesión.
        -   `logout()`: Elimina la información de la sesión del `localStorage`.
        -   `isLoggedIn()`: Verifica si hay una sesión activa.
        -   `getToken()`, `getUsername()`, `getRol()`, `getNombre()`: Recuperan la información del usuario almacenada.

-   **frontend/poc-emision-frontend/src/app/services/validacion.ts**
    -   **Que hace:** Es el cliente HTTP para interactuar con la API de validación del backend. Permite enviar archivos macro para su análisis y recibir el reporte de validación.
    -   **Metodos clave:**
        -   `validarMacro()`: Envía un archivo `File` junto con el tipo de acción y producto al endpoint `/api/v1/validacion/macro` del backend, observando los eventos HTTP para reportar el progreso de la carga.

-   **frontend/poc-emision-frontend/src/app/guards/auth-guard.ts**
    -   **Que hace:** Un *guard* de ruta en Angular que protege el acceso a ciertas partes de la aplicación. Solo permite el acceso a usuarios que estén logueados y que tengan el rol de 'broker', redirigiendo a la página de login si no cumplen estas condiciones.
    -   **Metodos clave:**
        -   `authGuard`: Función principal que implementa la lógica de protección de ruta.

-   **frontend/poc-emision-frontend/src/app/interceptors/auth.interceptor.ts**
    -   **Que hace:** Es un interceptor HTTP funcional que añade automáticamente el token de autenticación (Bearer token) a todas las peticiones salientes dirigidas a la API del backend, siempre y cuando exista un token en el `localStorage`.
    -   **Metodos clave:**
        -   `authInterceptor`: Función que clona la petición HTTP y añade el encabezado `Authorization`.

-   **frontend/poc-emision-frontend/src/app/components/login/login.ts**
    -   **Que hace:** Componente que gestiona la interfaz de usuario y la lógica para el inicio de sesión. Captura las credenciales del usuario, las envía al `AuthService` y maneja la navegación post-login, así como la visualización de mensajes de error.
    -   **Metodos clave:**
        -   `login()`: Método que se ejecuta al intentar iniciar sesión, validando las credenciales y el rol del usuario.


-   **frontend/poc-emision-frontend/src/app/app.ts**
    -   **Que hace:** Es el componente raíz de la aplicación Angular. Su función principal es renderizar el `<router-outlet />`, que es donde Angular inyecta los componentes de las rutas activas, sirviendo como el contenedor principal de la aplicación.
    -   **Metodos clave:** No tiene métodos propios significativos, su rol es estructural.

-   **frontend/poc-emision-frontend/src/app/components/dashboard/dashboard.ts**
    -   **Que hace:** Proporciona la vista de entrada al portal una vez que el usuario ha iniciado sesión. Muestra un resumen de los expedientes del usuario (casos abiertos, por tipo de acción, observados) y permite navegar a los diferentes procesos o ver los detalles de un expediente.
    -   **Metodos clave:**
        -   `cargarCasos()`: Obtiene la lista de expedientes del usuario desde el servicio de casos.
        -   `setFiltro()`: Permite filtrar la lista de expedientes mostrados en el dashboard.
        -   `abrirProceso()`: Navega al componente de proceso de GMM (nueva o renovación).
        -   `verExpediente()`: Navega a la vista de detalle de un expediente específico.

-   **frontend/poc-emision-frontend/src/app/components/nueva-gmm/nueva-gmm.ts**
    -   **Que hace:** Es un componente *wrapper* simple que encapsula el `GmmProcesoComponent` para el tipo de acción "nueva" en GMM. Su propósito es definir una ruta específica para este flujo.
    -   **Metodos clave:** No tiene métodos propios, su función es delegar al `GmmProcesoComponent`.

-   **frontend/poc-emision-frontend/src/app/components/renovacion-gmm/renovacion-gmm.ts**
    -   **Que hace:** Similar a `NuevaGmmComponent`, este es un componente *wrapper* que encapsula el `GmmProcesoComponent` para el tipo de acción "renovación" en GMM, permitiendo una ruta y contexto específicos para este flujo.
    -   **Metodos clave:** No tiene métodos propios, su función es delegar al `GmmProcesoComponent`.