"""
Pipeline de carga y preprocesamiento de documentos para AD_ASTRA.

Orquesta: Loader → TextCleaner → lista de Documents listos para chunking.
"""
from __future__ import annotations

from pathlib import Path
from typing import Union

from core.document import Document
from loaders.base_loader import BaseLoader
from loaders.csv_loader import CSVLoader
from loaders.html_loader import HTMLLoader
from loaders.json_loader import JSONLoader
from loaders.markdown_loader import MarkdownLoader
from loaders.pdf_loader import PDFLoader
from loaders.remote_loader import RemoteLoader
from loaders.txt_loader import TXTLoader
from loaders.xlsx_loader import XLSXLoader
from preprocessing.cleaner import TextCleaner


# Mapa extensión → loader por defecto
_EXTENSION_LOADER_MAP: dict[str, type[BaseLoader]] = {
    ".pdf":      PDFLoader,
    ".html":     HTMLLoader,
    ".htm":      HTMLLoader,
    ".json":     JSONLoader,
    ".csv":      CSVLoader,
    ".xlsx":     XLSXLoader,
    ".xls":      XLSXLoader,
    ".md":       MarkdownLoader,
    ".markdown": MarkdownLoader,
    ".txt":      TXTLoader,
}


def get_loader_for_source(source: Union[str, Path]) -> BaseLoader:
    """
    Selecciona automáticamente el loader adecuado según la extensión
    del archivo o si la fuente es una URL.

    Args:
        source: Ruta local o URL.

    Returns:
        Instancia del loader correspondiente.

    Raises:
        ValueError: Si no se puede determinar el loader.
    """
    s = str(source)
    if s.startswith("http://") or s.startswith("https://"):
        return RemoteLoader()

    ext = Path(s).suffix.lower()
    loader_cls = _EXTENSION_LOADER_MAP.get(ext)
    if loader_cls is None:
        raise ValueError(
            f"No hay loader disponible para la extensión '{ext}'. "
            f"Extensiones soportadas: {list(_EXTENSION_LOADER_MAP.keys())}"
        )
    return loader_cls()


def load_and_clean(
    sources: list[Union[str, Path]],
    cleaner: TextCleaner | None = None,
    loader: BaseLoader | None = None,
) -> list[Document]:
    """
    Carga documentos desde múltiples fuentes y los limpia.

    Args:
        sources:  Lista de rutas o URLs.
        cleaner:  Instancia de TextCleaner. Si es None, usa configuración por defecto.
        loader:   Loader a usar para todas las fuentes. Si es None, se
                  selecciona automáticamente por extensión/URL.

    Returns:
        Lista de Documents limpios listos para chunking.
    """
    if cleaner is None:
        cleaner = TextCleaner()

    documents: list[Document] = []
    for source in sources:
        active_loader = loader or get_loader_for_source(source)
        docs = active_loader.load(source)
        documents.extend(docs)

    return cleaner.clean_many(documents)
