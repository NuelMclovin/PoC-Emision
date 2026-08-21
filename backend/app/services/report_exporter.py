import io
import pandas as pd
from typing import Literal

def exportar_df_a_archivo(
    df: pd.DataFrame,
    original_filename: str,
    formato: Literal["csv", "excel"]
) -> tuple[io.BytesIO, str, str]:
    """
    Exporta un DataFrame de Pandas a un archivo CSV o Excel en un buffer de memoria.

    Args:
        df: DataFrame de Pandas a exportar.
        original_filename: Nombre del archivo original para generar el nombre de exportación.
        formato: Formato deseado ('csv' o 'excel').

    Returns:
        Una tupla con:
        - io.BytesIO: Buffer de memoria con el contenido del archivo.
        - str: Content-Type (media type) del archivo.
        - str: Nombre de archivo sugerido para la descarga.
    """
    output = io.BytesIO()
    # Obtener el nombre sin extensión, manejando casos donde no haya extensión o haya múltiples puntos
    base_name = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
    
    if formato == "csv":
        df.to_csv(output, index=False, encoding='utf-8-sig') # 'utf-8-sig' para BOM en CSV
        media_type = "text/csv"
        filename_export = f"errores_{base_name}.csv"
    elif formato == "excel":
        # Usar XlsxWriter como motor para mejor compatibilidad y opciones
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Errores')
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename_export = f"errores_{base_name}.xlsx" # <--- ¡Asegúrate de que esta línea sea exactamente así!
    else:
        # Esto no debería ocurrir debido al Literal type, pero es buena práctica
        raise ValueError("Formato de exportación no soportado.")
    
    output.seek(0) # Rebobinar el buffer al inicio para poder leerlo
    return output, media_type, filename_export
