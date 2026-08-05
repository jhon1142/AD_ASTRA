"""
Parser para imágenes con OCR.

El spec indica que cuando la imagen contiene texto relevante
(infografías, gráficos), se aplica OCR para recuperar el texto.
Requiere: pytesseract, Pillow + Tesseract instalado en el sistema.
"""
from __future__ import annotations

from pathlib import Path
from typing import Union

from config.settings import OCR_LANGUAGES, OCR_CONFIG
from core.document import Document
from data.parsers.base_loader import BaseLoader, infer_fenomeno, make_doc_id

SUPPORTED = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp", ".gif"}


class ImageLoader(BaseLoader):
    """
    Extrae texto de imágenes usando Tesseract OCR.

    Args:
        lang:   Idiomas Tesseract, e.g. 'spa+eng+por'.
        config: Configuración adicional de Tesseract.
    """

    def __init__(
        self,
        lang: str = OCR_LANGUAGES,
        config: str = OCR_CONFIG,
    ) -> None:
        self.lang   = lang
        self.config = config

    def load(self, source: Union[str, Path]) -> list[Document]:
        try:
            import pytesseract
            from PIL import Image
        except ImportError as exc:
            raise ImportError(
                "Instala: pip install pytesseract Pillow\n"
                "Y Tesseract: https://github.com/tesseract-ocr/tesseract"
            ) from exc

        path = Path(source)
        if path.suffix.lower() not in SUPPORTED:
            raise ValueError(
                f"Extensión no soportada por ImageLoader: {path.suffix}. "
                f"Soportadas: {sorted(SUPPORTED)}"
            )

        image = Image.open(str(path))
        text  = pytesseract.image_to_string(image, lang=self.lang, config=self.config)

        return [
            Document(
                doc_id   = make_doc_id(path),
                fuente   = path.name,
                formato  = "image",
                fenomeno = infer_fenomeno(path),
                content  = text,
                metadata = {
                    "ruta_completa": str(path),
                    "formato_imagen": image.format,
                    "dimensiones": image.size,
                    "ocr_lang": self.lang,
                    "ocr": True,
                },
            )
        ]
