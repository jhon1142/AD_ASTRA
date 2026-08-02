"""
Clase base abstracta para todos los loaders de AD_ASTRA.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union

from core.document import Document


class BaseLoader(ABC):
    """
    Interfaz común que deben implementar todos los loaders.
    """

    @abstractmethod
    def load(self, source: Union[str, Path]) -> list[Document]:
        """
        Carga documentos desde la fuente indicada.

        Args:
            source: Ruta al archivo / URL / cadena de texto.

        Returns:
            Lista de objetos Document.
        """

    def load_many(self, sources: list[Union[str, Path]]) -> list[Document]:
        """
        Carga documentos desde múltiples fuentes.

        Args:
            sources: Lista de rutas o URLs.

        Returns:
            Lista concatenada de objetos Document.
        """
        documents: list[Document] = []
        for source in sources:
            documents.extend(self.load(source))
        return documents
