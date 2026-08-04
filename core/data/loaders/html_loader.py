"""
Loader para archivos HTML.
Requiere: beautifulsoup4, lxml
"""
from pathlib import Path
from typing import Union

from config.settings import DEFAULT_ENCODING
from core.document import Document
from data.loaders.base_loader import BaseLoader


class HTMLLoader(BaseLoader):
    """
    Extrae el texto visible de un archivo HTML local.
    """

    def __init__(self, encoding: str = DEFAULT_ENCODING, parser: str = "lxml") -> None:
        self.encoding = encoding
        self.parser = parser

    def load(self, source: Union[str, Path]) -> list[Document]:
        """
        Args:
            source: Ruta al archivo HTML.

        Returns:
            Lista con un único Document con el texto extraído.
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError as exc:
            raise ImportError("Instala 'beautifulsoup4': pip install beautifulsoup4 lxml") from exc

        path = Path(source)
        html = path.read_text(encoding=self.encoding)
        soup = BeautifulSoup(html, self.parser)

        # Eliminar scripts y estilos
        for tag in soup(["script", "style"]):
            tag.decompose()

        text = soup.get_text(separator="\n")

        return [
            Document(
                content=text,
                metadata={
                    "source": str(path),
                    "file_type": "html",
                    "title": soup.title.string if soup.title else "",
                },
            )
        ]
