"""
Parser para archivos HTML locales.
Requiere: beautifulsoup4, lxml
"""
from __future__ import annotations

from pathlib import Path
from typing import Union

from config.settings import DEFAULT_ENCODING
from core.document import Document
from data.parsers.base_loader import BaseLoader, infer_fenomeno, make_doc_id


class HTMLLoader(BaseLoader):
    """
    Extrae el texto visible de un archivo HTML.

    Elimina scripts, estilos y markup. Preserva la estructura
    de encabezados/párrafos con saltos de línea.

    Args:
        encoding: Codificación del archivo.
        parser:   Parser de BeautifulSoup ('lxml' o 'html.parser').
    """

    def __init__(
        self,
        encoding: str = DEFAULT_ENCODING,
        parser: str = "lxml",
    ) -> None:
        self.encoding = encoding
        self.parser = parser

    def load(self, source: Union[str, Path]) -> list[Document]:
        try:
            from bs4 import BeautifulSoup
        except ImportError as exc:
            raise ImportError(
                "Instala: pip install beautifulsoup4 lxml"
            ) from exc

        path = Path(source)
        html = path.read_text(encoding=self.encoding, errors="replace")
        soup = BeautifulSoup(html, self.parser)

        # Eliminar elementos no textuales
        for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
            tag.decompose()

        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        text  = soup.get_text(separator="\n")

        return [
            Document(
                doc_id   = make_doc_id(path),
                fuente   = path.name,
                formato  = "html",
                fenomeno = infer_fenomeno(path),
                content  = text,
                metadata = {
                    "ruta_completa": str(path),
                    "titulo": title,
                },
            )
        ]
