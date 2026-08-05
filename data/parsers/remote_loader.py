"""
Parser para fuentes remotas (URLs HTTP/HTTPS).
Requiere: requests, beautifulsoup4
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Union
from urllib.parse import urlparse

from config.settings import REMOTE_TIMEOUT
from core.document import Document
from data.parsers.base_loader import BaseLoader, infer_fenomeno


def _url_doc_id(url: str) -> str:
    """Genera doc_id reproducible desde una URL."""
    return hashlib.sha256(url.encode()).hexdigest()[:12]


class RemoteLoader(BaseLoader):
    """
    Descarga contenido desde una URL y extrae su texto.

    Detecta el tipo de contenido automáticamente:
    - text/html  → extrae texto visible con BeautifulSoup
    - text/plain → devuelve el texto directamente
    - application/json → devuelve el JSON como string

    Args:
        timeout:  Segundos de espera máximos.
        fenomeno: Fenómeno al que pertenece la URL (0 = desconocido).
    """

    def __init__(
        self,
        timeout: int = REMOTE_TIMEOUT,
        fenomeno: int = 0,
    ) -> None:
        self.timeout  = timeout
        self.fenomeno = fenomeno

    def load(self, source: Union[str, Path]) -> list[Document]:
        try:
            import requests
        except ImportError as exc:
            raise ImportError("Instala: pip install requests") from exc

        url      = str(source)
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "")
        domain       = urlparse(url).netloc

        if "text/html" in content_type:
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, "lxml")
                for tag in soup(["script", "style", "nav", "footer"]):
                    tag.decompose()
                title = soup.title.string.strip() if soup.title and soup.title.string else ""
                text  = soup.get_text(separator="\n")
            except ImportError:
                title = ""
                text  = response.text
        else:
            title = ""
            text  = response.text

        # Inferir fenomeno de la URL si no se especificó
        fenomeno = self.fenomeno or infer_fenomeno(url)

        return [
            Document(
                doc_id   = _url_doc_id(url),
                fuente   = url,
                formato  = "html" if "text/html" in content_type else "remote",
                fenomeno = fenomeno,
                content  = text,
                metadata = {
                    "url": url,
                    "dominio": domain,
                    "content_type": content_type,
                    "status_code": response.status_code,
                    "titulo": title,
                },
            )
        ]
