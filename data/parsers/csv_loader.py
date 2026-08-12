"""
Parser para archivos CSV.

Según el spec: leer la cabecera y recorrer registros uno a uno,
obteniendo cada fila como pares columna:valor. Cada fila puede
tratarse como unidad de fragmentación independiente.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Union

from config.settings import DEFAULT_ENCODING
from core.document import Document
from data.parsers.base_loader import (
    BaseLoader,
    infer_fenomeno,
    make_doc_id,
)


class CSVLoader(BaseLoader):
    """
    Parsea un archivo CSV. Produce un Document por fila.

    Cada valor conserva el nombre de su columna como contexto,
    formateado como "columna: valor | columna: valor ...".

    Args:
        content_columns: Columnas a incluir en el contenido.
                         None = todas las columnas.
        delimiter:       Separador de campos.
        encoding:        Codificación del archivo.
        skip_empty:      Si True, omite filas completamente vacías.
    """

    def __init__(
        self,
        content_columns: list[str] | None = None,
        delimiter: str = ",",
        encoding: str = DEFAULT_ENCODING,
        skip_empty: bool = True,
    ) -> None:
        self.content_columns = content_columns
        self.delimiter = delimiter
        self.encoding = encoding
        self.skip_empty = skip_empty

    def load(self, source: Union[str, Path]) -> list[Document]:
        path        = Path(source)
        doc_id_base = make_doc_id(path)
        fenomeno    = infer_fenomeno(path)
        documents: list[Document] = []

        with path.open(
            encoding=self.encoding,
            errors="replace",
            newline=""
        ) as f:
            reader = csv.DictReader(f, delimiter=self.delimiter)

            for row_num, row in enumerate(reader, start=1):
                cols = self.content_columns or list(row.keys())

                # Formato:
                # "columna: valor | columna: valor"
                parts = []

                for c in cols:
                    value = row.get(c, "")

                    if value is None:
                        continue

                    value_str = str(value).strip()

                    if value_str:
                        parts.append(f"{c}: {value_str}")

                if self.skip_empty and not parts:
                    continue

                content = " | ".join(parts)

                documents.append(
                    Document(
                        doc_id   = f"{doc_id_base}_{row_num:05d}",
                        fuente   = path.name,
                        formato  = "csv",
                        fenomeno = fenomeno,
                        content  = content,
                        metadata = {
                            "ruta_completa": str(path),
                            "fila": row_num,
                        },
                    )
                )

        return documents