"""
Parser para archivos Markdown (.md, .markdown).

El spec indica que los encabezados (#, ##) son señales útiles
de segmentación. El parser los preserva en el contenido y opcionalmente
divide el documento en secciones.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Union

from config.settings import DEFAULT_ENCODING
from core.document import Document
from data.parsers.base_loader import BaseLoader, infer_fenomeno, make_doc_id


class MarkdownLoader(BaseLoader):
    """
    Parsea un archivo Markdown.

    Args:
        split_by_heading: Si True, cada sección (H1/H2) → un Document.
                          Si False, el archivo completo → un Document.
        encoding:         Codificación del archivo.
    """

    _HEADING_RE = re.compile(r"^(#{1,2} .+)$", re.MULTILINE)

    def __init__(
        self,
        split_by_heading: bool = False,
        encoding: str = DEFAULT_ENCODING,
    ) -> None:
        self.split_by_heading = split_by_heading
        self.encoding         = encoding

    def load(self, source: Union[str, Path]) -> list[Document]:
        path     = Path(source)
        text     = path.read_text(encoding=self.encoding, errors="replace")
        doc_base = make_doc_id(path)
        fenomeno = infer_fenomeno(path)

        if not self.split_by_heading:
            return [
                Document(
                    doc_id   = doc_base,
                    fuente   = path.name,
                    formato  = "md",
                    fenomeno = fenomeno,
                    content  = text,
                    metadata = {"ruta_completa": str(path)},
                )
            ]

        # Dividir por encabezados H1/H2
        splits          = self._HEADING_RE.split(text)
        documents       = []
        current_heading = ""

        for i, chunk in enumerate(splits):
            chunk = chunk.strip()
            if not chunk:
                continue
            if self._HEADING_RE.match(chunk):
                current_heading = chunk.lstrip("#").strip()
            else:
                documents.append(
                    Document(
                        doc_id   = f"{doc_base}_{len(documents):04d}",
                        fuente   = path.name,
                        formato  = "md",
                        fenomeno = fenomeno,
                        content  = chunk,
                        metadata = {
                            "ruta_completa": str(path),
                            "seccion": current_heading,
                        },
                    )
                )

        # Fallback si no se encontraron secciones
        if not documents:
            return [
                Document(
                    doc_id   = doc_base,
                    fuente   = path.name,
                    formato  = "md",
                    fenomeno = fenomeno,
                    content  = text,
                    metadata = {"ruta_completa": str(path)},
                )
            ]

        return documents
