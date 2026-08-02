"""
Loader para archivos Markdown (.md, .markdown).
"""
import re
from pathlib import Path
from typing import Union

from config.settings import DEFAULT_ENCODING
from core.document import Document
from loaders.base_loader import BaseLoader


class MarkdownLoader(BaseLoader):
    """
    Carga un archivo Markdown.

    Args:
        split_by_heading: Si True, divide el documento en secciones por
                          encabezados de nivel 1 o 2 (# / ##).
        encoding:         Codificación del archivo.
    """

    def __init__(
        self,
        split_by_heading: bool = False,
        encoding: str = DEFAULT_ENCODING,
    ) -> None:
        self.split_by_heading = split_by_heading
        self.encoding = encoding

    def load(self, source: Union[str, Path]) -> list[Document]:
        path = Path(source)
        text = path.read_text(encoding=self.encoding)

        if not self.split_by_heading:
            return [
                Document(
                    content=text,
                    metadata={"source": str(path), "file_type": "markdown"},
                )
            ]

        # Divide por headings H1/H2
        pattern = re.compile(r"^(#{1,2} .+)$", re.MULTILINE)
        splits = pattern.split(text)

        documents: list[Document] = []
        current_heading = ""
        for chunk in splits:
            chunk = chunk.strip()
            if not chunk:
                continue
            if pattern.match(chunk):
                current_heading = chunk.lstrip("#").strip()
            else:
                documents.append(
                    Document(
                        content=chunk,
                        metadata={
                            "source": str(path),
                            "file_type": "markdown",
                            "heading": current_heading,
                        },
                    )
                )

        return documents or [Document(content=text, metadata={"source": str(path), "file_type": "markdown"})]
