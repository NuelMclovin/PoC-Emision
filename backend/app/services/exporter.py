from __future__ import annotations

from typing import List, Dict, Tuple
import pandas as pd
from io import BytesIO

def exportar_errores_csv(headers: List[str], filas: List[Dict[str, object]]) -> bytes:
    df = pd.DataFrame(filas, columns=headers)
    buf = BytesIO()
    df.to_csv(buf, index=False, encoding='utf-8')
    return buf.getvalue()

def exportar_errores_xlsx(headers: List[str], filas: List[Dict[str, object]]) -> bytes:
    df = pd.DataFrame(filas, columns=headers)
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Errores')
    return buf.getvalue()

def exportar_errores(headers: List[str], filas: List[Dict[str, object]], formato: str) -> Tuple[bytes, str, str]:
    if formato.lower() == 'csv':
        data = exportar_errores_csv(headers, filas)
        mime = 'text/csv'
        filename = 'errores.csv'
    else:
        data = exportar_errores_xlsx(headers, filas)
        mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        filename = 'errores.xlsx'
    return data, mime, filename
