"""
Modelo base de documento para el proyecto AD_ASTRA.
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Document:
    """
    Representa un documento cargado en el sistema.

    Attributes:
        content:  Texto plano del documento.
        metadata: Diccionario con metadatos (fuente, página, tipo, etc.).
        doc_id:   Identificador único opcional.
    """
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    doc_id: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.content, str):
            raise TypeError(f"content debe ser str, se recibió {type(self.content)}")

    def __repr__(self) -> str:
        snippet = self.content[:80].replace("\n", " ")
        return f"Document(id={self.doc_id!r}, chars={len(self.content)}, preview={snippet!r})"
