"""
Parser para archivos JSON.

El spec recomienda seleccionar explícitamente los campos de texto
(title, body_text, body_paragraphs) y conservar los descriptivos
(url, date, authors) como metadata.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Union

from config.settings import DEFAULT_ENCODING
from core.document import Document
from data.parsers.base_loader import BaseLoader, infer_fenomeno, make_doc_id


# Campos que se concatenan como contenido del documento (en orden de prioridad)
_CONTENT_FIELDS = [
    "body_text", "body_paragraphs", "content", "text",
    "full_text", "article", "abstract", "description",
]

# Campos que van a metadata en lugar del contenido
_META_FIELDS = {
    "url", "link", "href", "date", "published_at", "created_at",
    "authors", "author", "tags", "category", "title", "id",
    "source", "language", "lang",
}


def _extract_content(item: dict) -> tuple[str, dict]:
    """
    Extrae el contenido textual y la metadata de un objeto JSON.

    Returns:
        (content, metadata)
    """
    # Buscar campos de contenido en orden de prioridad
    for field in _CONTENT_FIELDS:
        val = item.get(field)
        if val:
            if isinstance(val, list):
                content = "\n\n".join(str(p) for p in val if p)
            else:
                content = str(val)
            # El resto va a metadata
            meta = {k: v for k, v in item.items() if k != field}
            return content, meta

    # Fallback: serializar el objeto completo
    return json.dumps(item, ensure_ascii=False), {}


class JSONLoader(BaseLoader):
    """
    Parsea un archivo JSON y produce un Document por elemento.

    Si el JSON es una lista, cada elemento → un Document.
    Si es un dict, el archivo completo → un Document.

    Args:
        content_key: Fuerza el uso de un campo específico como contenido.
                     None = detección automática.
        encoding:    Codificación del archivo.
    """

    def __init__(
        self,
        content_key: str | None = None,
        encoding: str = DEFAULT_ENCODING,
    ) -> None:
        self.content_key = content_key
        self.encoding = encoding

    def load(self, source: Union[str, Path]) -> list[Document]:
        path = Path(source)
        raw  = json.loads(path.read_text(encoding=self.encoding, errors="replace"))

        items = raw if isinstance(raw, list) else [raw]
        doc_id_base = make_doc_id(path)
        fenomeno    = infer_fenomeno(path)
        documents: list[Document] = []

        for idx, item in enumerate(items):
            if isinstance(item, dict):
                if self.content_key:
                    content = str(item.get(self.content_key, ""))
                    meta    = {k: v for k, v in item.items() if k != self.content_key}
                else:
                    content, meta = _extract_content(item)
            else:
                content = str(item)
                meta    = {}

            if not content.strip():
                continue

            # doc_id único por elemento si hay múltiples
            doc_id = doc_id_base if len(items) == 1 else f"{doc_id_base}_{idx:04d}"

            documents.append(
                Document(
                    doc_id   = doc_id,
                    fuente   = path.name,
                    formato  = "json",
                    fenomeno = fenomeno,
                    content  = content,
                    metadata = {
                        "ruta_completa": str(path),
                        "indice": idx,
                        **{k: v for k, v in meta.items()
                           if isinstance(v, (str, int, float, bool)) or v is None},
                    },
                )
            )

        return documents
