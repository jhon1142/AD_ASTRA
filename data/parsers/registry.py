"""
ParserRegistry — selecciona automáticamente el parser adecuado
según la extensión del archivo o si la fuente es una URL.

Centraliza la lógica que antes estaba dispersa en load_documents.py.
"""
from __future__ import annotations

from pathlib import Path
from typing import Union

from data.parsers.base_loader import BaseLoader
from data.parsers.csv_loader import CSVLoader
from data.parsers.html_loader import HTMLLoader
from data.parsers.image_loader import ImageLoader
from data.parsers.json_loader import JSONLoader
from data.parsers.markdown_loader import MarkdownLoader
from data.parsers.pbf_loader import PBFLoader
from data.parsers.pdf_loader import PDFLoader
from data.parsers.remote_loader import RemoteLoader
from data.parsers.txt_loader import TXTLoader
from data.parsers.xlsx_loader import XLSXLoader


class ParserRegistry:
    """
    Registro centralizado de parsers por extensión de archivo.

    Permite registrar nuevos parsers sin modificar el pipeline.

    Uso:
        registry = ParserRegistry()
        parser = registry.get(".pdf")          # por extensión
        parser = registry.get_for("doc.html")  # por ruta/URL
    """

    _DEFAULT: dict[str, type[BaseLoader]] = {
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
        ".png":      ImageLoader,
        ".jpg":      ImageLoader,
        ".jpeg":     ImageLoader,
        ".tiff":     ImageLoader,
        ".tif":      ImageLoader,
        ".bmp":      ImageLoader,
        ".webp":     ImageLoader,
        ".pbf":      PBFLoader,
    }

    def __init__(self) -> None:
        self._registry: dict[str, type[BaseLoader]] = dict(self._DEFAULT)

    def register(self, extension: str, parser_cls: type[BaseLoader]) -> None:
        """
        Registra un parser para una extensión.

        Args:
            extension:  Extensión con punto, ej. '.docx'.
            parser_cls: Clase del parser (subclase de BaseLoader).
        """
        self._registry[extension.lower()] = parser_cls

    def get(self, extension: str) -> BaseLoader:
        """
        Devuelve una instancia del parser para la extensión dada.

        Raises:
            ValueError: Si no hay parser registrado para esa extensión.
        """
        cls = self._registry.get(extension.lower())
        if cls is None:
            available = sorted(self._registry.keys())
            raise ValueError(
                f"No hay parser para '{extension}'. "
                f"Extensiones soportadas: {available}"
            )
        return cls()

    def get_for(self, source: Union[str, Path]) -> BaseLoader:
        """
        Selecciona el parser adecuado para una ruta o URL.

        Args:
            source: Ruta local o URL (http/https).

        Returns:
            Instancia del parser correspondiente.
        """
        s = str(source)
        if s.startswith("http://") or s.startswith("https://"):
            return RemoteLoader()
        ext = Path(s).suffix.lower()
        return self.get(ext)

    def supported_extensions(self) -> list[str]:
        """Lista de extensiones registradas."""
        return sorted(self._registry.keys())


# Instancia global reutilizable
default_registry = ParserRegistry()
