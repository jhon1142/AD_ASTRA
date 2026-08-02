"""
Loader para fuentes remotas (URLs).
Requiere: requests, beautifulsoup4, lxml
"""
from typing import Union
from pathlib import Path

from config.settings import REMOTE_TIMEOUT
from core.document import Document
from loaders.base_loader import BaseLoader


class RemoteLoader(BaseLoader):
    """
    Descarga contenido desde una URL y extrae su texto.

    Soporta:
    - text/html  → extrae texto visible con BeautifulSoup
    - text/plain → devuelve el texto directamente
    - application/json → devuelve el JSON como string

    Args:
        timeout: Tiempo máximo de espera en segundos.
    """

    def __init__(self, timeout: int = REMOTE_TIMEOUT) -> None:
        self.timeout = timeout

    def load(self, source: Union[str, Path]) -> list[Document]:
        """
        Args:
            source: URL completa (http/https).

        Returns:
            Lista con un Document con el contenido descargado.
        """
        try:
            import requests
        except ImportError as exc:
            raise ImportError("Instala 'requests': pip install requests") from exc

        url = str(source)
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "")
        text = ""

        if "text/html" in content_type:
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, "lxml")
                for tag in soup(["script", "style"]):
                    tag.decompose()
                text = soup.get_text(separator="\n")
            except ImportError:
                text = response.text
        else:
            text = response.text

        return [
            Document(
                content=text,
                metadata={
                    "source": url,
                    "file_type": "remote",
                    "content_type": content_type,
                    "status_code": response.status_code,
                },
            )
        ]
