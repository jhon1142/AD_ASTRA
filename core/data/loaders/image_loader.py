"""
Loader para imágenes con extracción de texto vía OCR.
Requiere: pytesseract, Pillow
"""
from pathlib import Path
from typing import Union

from core.document import Document
from data.loaders.base_loader import BaseLoader

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".gif", ".webp"}


class ImageLoader(BaseLoader):
    """
    Extrae texto de imágenes usando Tesseract OCR.

    Args:
        lang:      Idioma(s) para Tesseract, e.g. 'spa', 'eng', 'spa+eng'.
        config:    Configuración adicional de Tesseract, e.g. '--psm 6'.
    """

    def __init__(self, lang: str = "spa+eng", config: str = "") -> None:
        self.lang = lang
        self.config = config

    def load(self, source: Union[str, Path]) -> list[Document]:
        try:
            import pytesseract
            from PIL import Image
        except ImportError as exc:
            raise ImportError(
                "Instala las dependencias: pip install pytesseract Pillow\n"
                "También necesitas Tesseract instalado en el sistema: "
                "https://github.com/tesseract-ocr/tesseract"
            ) from exc

        path = Path(source)
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Extensión no soportada: {path.suffix}. Soportadas: {SUPPORTED_EXTENSIONS}")

        image = Image.open(str(path))
        text = pytesseract.image_to_string(image, lang=self.lang, config=self.config)

        return [
            Document(
                content=text,
                metadata={
                    "source": str(path),
                    "file_type": "image",
                    "format": image.format,
                    "size": image.size,
                    "ocr_lang": self.lang,
                },
            )
        ]
