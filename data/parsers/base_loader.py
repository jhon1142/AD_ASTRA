"""
Clase base abstracta para todos los parsers de AD_ASTRA.

Cada parser recibe una ruta/URL y devuelve uno o más Document
con los campos obligatorios del spec (doc_id, fuente, formato, fenomeno, content).
"""
from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union

from core.document import Document


def infer_fenomeno(path: Union[str, Path]) -> int:
    """
    Infiere el fenómeno temático (1, 2 o 3) a partir de la ruta del archivo.

    Busca F1, F2 o F3 en cualquier parte de la ruta.
    Devuelve 0 si no se puede determinar.
    """
    s = str(path).upper()
    if "F1" in s or "F1_" in s:
        return 1
    if "F2" in s or "F2_" in s:
        return 2
    if "F3" in s or "F3_" in s:
        return 3
    return 0


def make_doc_id(path: Union[str, Path]) -> str:
    """
    Genera un doc_id reproducible a partir de la ruta del archivo.
    Formato: primeras 12 hex del SHA-256 de la ruta normalizada.
    """
    normalized = str(Path(path).resolve())
    return hashlib.sha256(normalized.encode()).hexdigest()[:12]


class BaseLoader(ABC):
    """
    Interfaz común para todos los parsers.

    Cada subclase implementa load() y devuelve Documents con
    los campos obligatorios del spec CODEFEST:
        doc_id   — hash reproducible de la fuente
        fuente   — nombre/ruta del archivo original
        formato  — extensión del archivo (pdf, html, csv, etc.)
        fenomeno — 1, 2 o 3 (inferido de la ruta)
        content  — texto extraído y limpio
    """

    @abstractmethod
    def load(self, source: Union[str, Path]) -> list[Document]:
        """
        Parsea la fuente y devuelve lista de Documents.

        Args:
            source: Ruta local al archivo o URL remota.

        Returns:
            Lista de Document con todos los campos obligatorios.
        """

    def load_many(self, sources: list[Union[str, Path]]) -> list[Document]:
        """Parsea múltiples fuentes y concatena los resultados."""
        documents: list[Document] = []
        for source in sources:
            documents.extend(self.load(source))
        return documents
