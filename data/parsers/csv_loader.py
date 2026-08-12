"""
Parser para archivos CSV — AD_ASTRA CODEFEST 2026.

Reglas:
- El archivo completo representa un único documento.
- Todas las filas comparten el mismo doc_id.
- Cada fila se conserva como unidad independiente de fragmentación.
- Cada valor se representa como columna: valor.
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
    Parsea un CSV preservando la identidad documental del archivo.

    Cada fila se devuelve temporalmente como un Document independiente
    para que el pipeline pueda limpiarla individualmente, pero todas
    comparten el mismo doc_id correspondiente al archivo original.

    Posteriormente SentenceSplitter convierte cada fila en un Chunk
    independiente con posicion y chunk_id únicos.
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

    def load(
        self,
        source: Union[str, Path],
    ) -> list[Document]:

        path = Path(source)

        # IMPORTANTE:
        # Un único doc_id por ARCHIVO, no por fila.
        doc_id = make_doc_id(path)

        fenomeno = infer_fenomeno(path)

        documents: list[Document] = []

        with path.open(
            encoding=self.encoding,
            errors="replace",
            newline="",
        ) as file:

            reader = csv.DictReader(
                file,
                delimiter=self.delimiter,
            )

            for row_num, row in enumerate(
                reader,
                start=1,
            ):

                cols = (
                    self.content_columns
                    or list(row.keys())
                )

                parts: list[str] = []

                for column in cols:

                    value = row.get(
                        column,
                        "",
                    )

                    if value is None:
                        continue

                    value_str = str(
                        value
                    ).strip()

                    if value_str:

                        parts.append(
                            f"{column}: {value_str}"
                        )

                if (
                    self.skip_empty
                    and not parts
                ):
                    continue

                content = " | ".join(
                    parts
                )

                documents.append(
                    Document(
                        # Todas las filas tienen el MISMO doc_id.
                        doc_id=doc_id,

                        fuente=path.name,
                        formato="csv",
                        fenomeno=fenomeno,

                        content=content,

                        metadata={
                            "ruta_completa": str(path),

                            # Número ordinal de la fila de datos.
                            "fila": row_num,

                            # Índice original base 0.
                            "fila_indice": row_num - 1,

                            "tipo_unidad": "fila",
                        },
                    )
                )

        return documents