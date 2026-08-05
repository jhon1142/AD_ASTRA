"""
Parser para archivos de texto plano (.txt).
"""
from __future__ import annotations

from pathlib import Path
from typing import Union

from config.settings import DEFAULT_ENCODING
from core.document import Document
from data.parsers.base_loader import BaseLoader, infer_fenomeno, make_doc_id


class TXTLoader(BaseLoader):
    """
    Carga un archivo de texto plano como un único Document.

    Args:
        encoding: Codificación del archivo.
    """

    def __init__(self, encoding: str = DEFAULT_ENCODING) -> None:
        self.encoding = encoding

    def load(self, source: Union[str, Path]) -> list[Document]:
        path = Path(source)
        text = path.read_text(encoding=self.encoding, errors="replace")

        return [
            Document(
                doc_id   = make_doc_id(path),
                fuente   = path.name,
                formato  = "txt",
                fenomeno = infer_fenomeno(path),
                content  = text,
                metadata = {"ruta_completa": str(path)},
            )
        ]
