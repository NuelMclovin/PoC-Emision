1) Casos en los que falla la lectura del archivo (antes de validar reglas)

1. Extensión no soportada. Ejemplos: .txt, .json, .xlsb.
2. Excel corrupto, protegido, o con error de estructura interna. Resultado: error al abrir/parsear el archivo.
3. CSV con encoding no reconocible. Resultado: no se puede decodificar con los encodings de fallback.
4. Archivo sin registros útiles. Caso típico: archivo vacío o con filas totalmente vacías.
5. Hoja esperada no encontrada (caso indirecto). No siempre truena lectura, pero cae a “primera hoja” y luego normalmente falla por columnas requeridas ausentes.
2) Casos comunes donde los datos no pasan validación (reglas de negocio)

1. Columnas obligatorias faltantes (RN-00).

- GMM: NOMBRE, APELLIDO_PATERNO, APELLIDO_MATERNO, FECHA_NACIMIENTO, FECHA_ANTIGUEDAD, PARENTESCO, CERTIFICADO.
- Renovación GMM además exige: TIPO_MOVIMIENTO, NUMERO_POLIZA.

1. Persona duplicada por clave compuesta (RN-01). Clave: apellidos + nombre + fecha_nacimiento + certificado.
2. Fecha de nacimiento inválida (RN-02).

- Formato inválido.
- Fecha futura.
- Fecha imposible (antes de 1900).
- Valor con hora en vez de fecha (por ejemplo “10:35 am”).

1. Antigüedad anterior al nacimiento (RN-03). FECHA_ANTIGUEDAD < FECHA_NACIMIENTO.
2. Certificado sin titular (RN-04). Un certificado debe tener al menos un registro con parentesco Titular.
3. Más de un cónyuge por certificado (RN-05).
4. Más de un titular por certificado (RN-06).
5. Edad fuera de límite (RN-07 / RN-08).

- Nueva: Titular/Cónyuge > 64.
- Renovación: Titular/Cónyuge > 70.
- Beneficiarios > 24.
- Excepción en renovación: hasta 75 si tiene endoso válido y comentario suficiente.
- 
75 siempre error.



1. Tipo de movimiento inválido en renovación (RN-09).

- Vacío o fuera del catálogo permitido (ALTA, BAJA, CAMBIO, etc.).
3) Casos no tan comunes (pero importantes para discusión)

1. Hora capturada en columna de fecha. Ejemplo: “8:30 p.m.” en FECHA_NACIMIENTO; se rechaza como no-fecha.
2. Fecha con formato ambiguo no soportado. Ejemplo: “31.12.2024” o “2024.12.31”.
3. Encabezados con variaciones fuertes que no caen en alias. Si el nombre de columna no mapea al alias, se reporta como faltante.
4. Hoja correcta no encontrada y lectura desde hoja equivocada. Da datos “leíbles” pero semánticamente incorrectos, luego detona múltiples errores de estructura.
5. Duplicidad de errores por edad/fecha en ciertos registros. Un registro puede caer tanto en “fecha inválida” como en “edad fuera de límite” según contenido y flujo de reglas.
6. Certificado vacío o con espacios. Puede agrupar registros de forma inesperada y disparar errores de titular/cónyuge.
