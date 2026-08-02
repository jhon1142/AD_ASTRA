"""
Loader para archivos de texto plano (.txt).
"""
from pathlib import Path
from typing import Union

from config.settings import DEFAULT_ENCODING
from core.document import Document
from data.loaders.base_loader import BaseLoader


class TXTLoader(BaseLoader):
    """
    Carga un archivo de texto plano.

    Args:
        encoding:        Codificación del archivo.
        split_by_lines:  Si True, cada línea no vacía es un Document separado.
    """

    def __init__(
        self,
        encoding: str = DEFAULT_ENCODING,
        split_by_lines: bool = False,
    ) -> None:
        self.encoding = encoding
        self.split_by_lines = split_by_lines

    def load(self, source: Union[str, Path]) -> list[Document]:
        path = Path(source)
        text = path.read_text(encoding=self.encoding)

        if not self.split_by_lines:
            return [
                Document(
                    content=text,
                    metadata={"source": str(path), "file_type": "txt"},
                )
            ]

        documents: list[Document] = []
        for line_num, line in enumerate(text.splitlines(), start=1):
            line = line.strip()
            if line:
                documents.append(
                    Document(
                        content=line,
                        metadata={"source": str(path), "file_type": "txt", "line": line_num},
                    )
                )
        return documents
