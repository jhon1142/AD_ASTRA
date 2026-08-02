"""
Loader para archivos PDF.
Requiere: pypdf
"""
from pathlib import Path
from typing import Union

from core.document import Document
from loaders.base_loader import BaseLoader


class PDFLoader(BaseLoader):
    """
    Carga el texto de cada página de un PDF como un Document separado.
    """

    def load(self, source: Union[str, Path]) -> list[Document]:
        """
        Args:
            source: Ruta al archivo PDF.

        Returns:
            Un Document por página del PDF.
        """
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ImportError("Instala 'pypdf': pip install pypdf") from exc

        path = Path(source)
        reader = PdfReader(str(path))
        documents: list[Document] = []

        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            documents.append(
                Document(
                    content=text,
                    metadata={
                        "source": str(path),
                        "page": page_num,
                        "total_pages": len(reader.pages),
                        "file_type": "pdf",
                    },
                )
            )

        return documents
