"""
Parser para archivos PDF.
Requiere: pypdf
"""
from __future__ import annotations

from pathlib import Path
from typing import Union

from core.document import Document
from data.parsers.base_loader import BaseLoader, infer_fenomeno, make_doc_id


class PDFLoader(BaseLoader):
    """
    Extrae el texto de cada página de un PDF.

    Produce un único Document por archivo con el texto completo concatenado.
    La paginación se preserva en metadata para trazabilidad.

    Args:
        preserve_layout: Si True, intenta mantener el orden de lectura.
    """

    def __init__(self, preserve_layout: bool = True) -> None:
        self.preserve_layout = preserve_layout

    def load(self, source: Union[str, Path]) -> list[Document]:
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ImportError("Instala 'pypdf': pip install pypdf") from exc

        path = Path(source)
        reader = PdfReader(str(path))
        total_pages = len(reader.pages)

        # Extraer texto de todas las páginas y concatenar
        pages_text: list[str] = []
        for page in reader.pages:
            text = page.extract_text() or ""
            if text.strip():
                pages_text.append(text)

        full_text = "\n\n".join(pages_text)

        return [
            Document(
                doc_id   = make_doc_id(path),
                fuente   = path.name,
                formato  = "pdf",
                fenomeno = infer_fenomeno(path),
                content  = full_text,
                metadata = {
                    "ruta_completa": str(path),
                    "total_paginas": total_pages,
                    "paginas_con_texto": len(pages_text),
                },
            )
        ]
