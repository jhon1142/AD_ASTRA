"""
Loader para archivos Excel (.xlsx / .xls).
Requiere: openpyxl
"""
from pathlib import Path
from typing import Union

from core.document import Document
from loaders.base_loader import BaseLoader


class XLSXLoader(BaseLoader):
    """
    Carga un archivo Excel y convierte cada fila en un Document.

    Args:
        sheet_name:      Nombre o índice de la hoja. None = primera hoja.
        content_columns: Columnas a usar como contenido. None = todas.
        header_row:      Fila que contiene los encabezados (0-indexed). Default 0.
    """

    def __init__(
        self,
        sheet_name: str | int | None = 0,
        content_columns: list[str] | None = None,
        header_row: int = 0,
    ) -> None:
        self.sheet_name = sheet_name
        self.content_columns = content_columns
        self.header_row = header_row

    def load(self, source: Union[str, Path]) -> list[Document]:
        try:
            import openpyxl
        except ImportError as exc:
            raise ImportError("Instala 'openpyxl': pip install openpyxl") from exc

        path = Path(source)
        wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)

        # Selección de hoja
        if isinstance(self.sheet_name, int):
            sheet = wb.worksheets[self.sheet_name]
        elif self.sheet_name is None:
            sheet = wb.active
        else:
            sheet = wb[self.sheet_name]

        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            return []

        headers = [str(h) if h is not None else f"col_{i}" for i, h in enumerate(rows[self.header_row])]
        data_rows = rows[self.header_row + 1 :]

        documents: list[Document] = []
        cols = self.content_columns or headers

        for row_num, row in enumerate(data_rows, start=self.header_row + 2):
            row_dict = dict(zip(headers, row))
            content = " | ".join(str(row_dict.get(c, "")) for c in cols)
            metadata = {
                "source": str(path),
                "sheet": sheet.title,
                "row": row_num,
                "file_type": "xlsx",
                **{k: v for k, v in row_dict.items() if k not in cols},
            }
            documents.append(Document(content=content, metadata=metadata))

        wb.close()
        return documents
