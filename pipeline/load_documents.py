"""
Pipeline de carga y preprocesamiento de documentos para AD_ASTRA.

Orquesta: ParserRegistry → TextCleaner → lista de Documents.
"""
from __future__ import annotations

from pathlib import Path
from typing import Union

from core.document import Document
from data.parsers.base_loader import BaseLoader
from data.parsers.registry import default_registry
from preprocessing.cleaner import TextCleaner


def load_and_clean(
    sources: list[Union[str, Path]],
    cleaner: TextCleaner | None = None,
    loader: BaseLoader | None = None,
) -> list[Document]:
    """
    Carga documentos desde múltiples fuentes y los limpia.

    Args:
        sources: Lista de rutas o URLs.
        cleaner: TextCleaner personalizado. None = configuración por defecto.
        loader:  Parser explícito. None = selección automática por extensión/URL.

    Returns:
        Lista de Documents limpios listos para chunking.
    """
    if cleaner is None:
        cleaner = TextCleaner()

    documents: list[Document] = []
    for source in sources:
        active_loader = loader or default_registry.get_for(source)
        docs = active_loader.load(source)
        documents.extend(docs)

    return cleaner.clean_many(documents)
