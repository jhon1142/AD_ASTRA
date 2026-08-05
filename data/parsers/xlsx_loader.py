"""
Parser para archivos Excel (.xlsx / .xls).
Requiere: openpyxl
"""
from __future__ import annotations

from pathlib import Path
from typing import Union

from core.document import Document
from data.parsers.base_loader import BaseLoader, infer_fenomeno, make_doc_id


class XLSXLoader(BaseLoader):
    """
    Parsea un archivo Excel. Produce un Document por fila con datos.

    Formato de contenido: "columna: valor | columna: valor ..."

    Args:
        sheet_name:      Hoja a leer. None = primera hoja activa.
        content_columns: Columnas a incluir. None = todas.
        header_row:      Índice de la fila de cabecera (0-indexed).
        skip_empty:      Omite filas completamente vacías.
    """

    def __init__(
        self,
        sheet_name: str | int | None = None,
        content_columns: list[str] | None = None,
        header_row: int = 0,
        skip_empty: bool = True,
    ) -> None:
        self.sheet_name      = sheet_name
        self.content_columns = content_columns
        self.header_row      = header_row
        self.skip_empty      = skip_empty

    def load(self, source: Union[str, Path]) -> list[Document]:
        try:
            import openpyxl
        except ImportError as exc:
            raise ImportError("Instala 'openpyxl': pip install openpyxl") from exc

        path     = Path(source)
        doc_base = make_doc_id(path)
        fenomeno = infer_fenomeno(path)

        wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)

        if isinstance(self.sheet_name, int):
            sheet = wb.worksheets[self.sheet_name]
        elif self.sheet_name is None:
            sheet = wb.active
        else:
            sheet = wb[self.sheet_name]

        rows = list(sheet.iter_rows(values_only=True))
        wb.close()

        if not rows:
            return []

        headers   = [
            str(h) if h is not None else f"col_{i}"
            for i, h in enumerate(rows[self.header_row])
        ]
        data_rows = rows[self.header_row + 1:]
        cols      = self.content_columns or headers

        documents: list[Document] = []
        for row_num, row in enumerate(data_rows, start=1):
            row_dict = dict(zip(headers, row))
            parts = [
                f"{c}: {row_dict.get(c, '')}"
                for c in cols
                if row_dict.get(c) is not None and str(row_dict.get(c, "")).strip()
            ]

            if self.skip_empty and not parts:
                continue

            content = " | ".join(parts)

            documents.append(
                Document(
                    doc_id   = f"{doc_base}_{row_num:05d}",
                    fuente   = path.name,
                    formato  = "xlsx",
                    fenomeno = fenomeno,
                    content  = content,
                    metadata = {
                        "ruta_completa": str(path),
                        "hoja": sheet.title,
                        "fila": self.header_row + 1 + row_num,
                    },
                )
            )

        return documents
