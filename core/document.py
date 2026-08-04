"""
Modelo de documento para AD_ASTRA — CODEFEST 2026.

Un documento corresponde a un archivo individual provisto por ADL
(PDF, HTML, TXT, CSV, XLSX, etc.). Tiene un doc_id único e inmutable.

Ref: Sección 2.3 de la especificación técnica.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Document:
    """
    Representa un archivo original del corpus ADL.

    Attributes:
        doc_id:   Identificador único e inmutable del documento.
                  Generado por el equipo a partir del hash del archivo.
        fuente:   Nombre o ruta del archivo original provisto por ADL.
                  Es la clave de emparejamiento con el ground truth.
        formato:  Formato del archivo: 'pdf', 'html', 'json', 'csv',
                  'xlsx', 'txt', 'md', 'image', 'pbf'.
        fenomeno: Fenómeno temático al que pertenece (1, 2 o 3).
        content:  Texto extraído y limpio del documento.
        metadata: Campos adicionales opcionales (título, fecha, idioma, etc.).
    """
    doc_id:   str
    fuente:   str
    formato:  str
    fenomeno: int
    content:  str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.doc_id:
            raise ValueError("doc_id no puede estar vacío")
        if self.fenomeno not in (1, 2, 3):
            raise ValueError(f"fenomeno debe ser 1, 2 o 3; se recibió {self.fenomeno}")
        if not isinstance(self.content, str):
            raise TypeError(f"content debe ser str, se recibió {type(self.content)}")

    @property
    def extension(self) -> str:
        """Devuelve la extensión del archivo fuente en minúsculas."""
        return Path(self.fuente).suffix.lower()

    def __repr__(self) -> str:
        snippet = self.content[:80].replace("\n", " ")
        return (
            f"Document(id={self.doc_id!r}, fuente={self.fuente!r}, "
            f"fenomeno={self.fenomeno}, chars={len(self.content)}, "
            f"preview={snippet!r})"
        )
