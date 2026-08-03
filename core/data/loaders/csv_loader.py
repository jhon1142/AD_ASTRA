"""
Loader para archivos CSV.
"""
import csv
from pathlib import Path
from typing import Union

from config.settings import DEFAULT_ENCODING
from core.document import Document
from data.loaders.base_loader import BaseLoader


class CSVLoader(BaseLoader):
    """
    Carga un archivo CSV y convierte cada fila en un Document.

    Args:
        content_columns: Lista de columnas que se concatenan como contenido.
                         Si es None, se usan todas las columnas.
        delimiter:       Separador de campos (defecto: ',').
        encoding:        Codificación del archivo.
    """

    def __init__(
        self,
        content_columns: list[str] | None = None,
        delimiter: str = ",",
        encoding: str = DEFAULT_ENCODING,
    ) -> None:
        self.content_columns = content_columns
        self.delimiter = delimiter
        self.encoding = encoding

    def load(self, source: Union[str, Path]) -> list[Document]:
        path = Path(source)
        documents: list[Document] = []

        with path.open(encoding=self.encoding, newline="") as f:
            reader = csv.DictReader(f, delimiter=self.delimiter)
            for row_num, row in enumerate(reader, start=1):
                cols = self.content_columns or list(row.keys())
                content = " | ".join(str(row.get(col, "")) for col in cols)
                metadata = {
                    "source": str(path),
                    "row": row_num,
                    "file_type": "csv",
                    **{k: v for k, v in row.items() if k not in cols},
                }
                documents.append(Document(content=content, metadata=metadata))

        return documents
