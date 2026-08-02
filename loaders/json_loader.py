"""
Loader para archivos JSON.
"""
import json
from pathlib import Path
from typing import Union

from config.settings import DEFAULT_ENCODING
from core.document import Document
from loaders.base_loader import BaseLoader


class JSONLoader(BaseLoader):
    """
    Carga un archivo JSON y convierte cada elemento (o el documento completo)
    en un Document.

    Si el JSON es una lista, cada elemento se convierte en un Document.
    Si es un diccionario, el documento completo se convierte en uno solo.

    Args:
        content_key: Clave del diccionario cuyo valor se usará como `content`.
                     Si es None, se serializa el objeto completo.
        encoding:    Codificación del archivo.
    """

    def __init__(self, content_key: str | None = None, encoding: str = DEFAULT_ENCODING) -> None:
        self.content_key = content_key
        self.encoding = encoding

    def load(self, source: Union[str, Path]) -> list[Document]:
        path = Path(source)
        data = json.loads(path.read_text(encoding=self.encoding))

        items = data if isinstance(data, list) else [data]
        documents: list[Document] = []

        for idx, item in enumerate(items):
            if self.content_key and isinstance(item, dict):
                content = str(item.get(self.content_key, ""))
                metadata = {k: v for k, v in item.items() if k != self.content_key}
            else:
                content = json.dumps(item, ensure_ascii=False)
                metadata = {}

            metadata.update({"source": str(path), "index": idx, "file_type": "json"})
            documents.append(Document(content=content, metadata=metadata))

        return documents
