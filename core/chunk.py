"""
Modelo de fragmento (chunk) para AD_ASTRA — CODEFEST 2026.

Un fragmento es la unidad mínima almacenada en la base vectorial.
Cada chunk deriva de un Document y tiene su propio chunk_id.

Ref: Secciones 3 y 3.4 de la especificación técnica.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Chunk:
    """
    Fragmento de texto derivado de un Document.

    Campos obligatorios según Tabla 1 del spec:
        chunk_id:   Identificador único del fragmento dentro del documento.
                    Formato recomendado: "{doc_id}-chunk-{posicion:04d}"
        doc_id:     Identificador del documento de origen.
        fuente:     Nombre o URL del archivo original provisto por ADL.
        formato:    Formato del archivo de origen: pdf, html, md, etc.
        fenomeno:   Fenómeno temático (1, 2 o 3).
        posicion:   Índice ordinal del fragmento dentro del documento (base 0).
        num_tokens: Número de tokens del fragmento.
        texto:      Texto original del fragmento, sin modificaciones.

    Campos opcionales (añadidos por el equipo):
        metadata:   Idioma, título, fecha de publicación, etc.
        faiss_id:   Identificador interno FAISS asignado al indexar.
    """
    # ── Campos obligatorios (Tabla 1) ────────────────────────────────────────
    chunk_id:   str
    doc_id:     str
    fuente:     str
    formato:    str
    fenomeno:   int
    posicion:   int
    num_tokens: int
    texto:      str

    # ── Campos opcionales ────────────────────────────────────────────────────
    metadata:   dict[str, Any] = field(default_factory=dict)
    faiss_id:   int = -1          # -1 = no indexado todavía

    def __post_init__(self) -> None:
        if not self.chunk_id:
            raise ValueError("chunk_id no puede estar vacío")
        if not self.doc_id:
            raise ValueError("doc_id no puede estar vacío")
        if self.fenomeno not in (1, 2, 3):
            raise ValueError(f"fenomeno debe ser 1, 2 o 3; se recibió {self.fenomeno}")
        if self.posicion < 0:
            raise ValueError("posicion debe ser >= 0")
        if self.num_tokens < 0:
            raise ValueError("num_tokens debe ser >= 0")

    @property
    def word_count(self) -> int:
        """Número de palabras del fragmento (estimación rápida)."""
        return len(self.texto.split())

    @property
    def exceeds_word_limit(self) -> bool:
        """True si el fragmento supera las 250 palabras (límite del spec)."""
        return self.word_count > 250

    def to_metadata_record(self) -> dict[str, Any]:
        """
        Serializa el chunk al formato del almacén de metadata (metadata.jsonl).
        Incluye todos los campos obligatorios de la Tabla 1 del spec.
        """
        record = {
            "chunk_id":   self.chunk_id,
            "doc_id":     self.doc_id,
            "fuente":     self.fuente,
            "formato":    self.formato,
            "fenomeno":   self.fenomeno,
            "posicion":   self.posicion,
            "num_tokens": self.num_tokens,
            "texto":      self.texto,
        }
        if self.faiss_id >= 0:
            record["faiss_id"] = self.faiss_id
        record.update(self.metadata)
        return record

    @classmethod
    def from_metadata_record(cls, record: dict[str, Any]) -> "Chunk":
        """
        Reconstruye un Chunk desde un registro del metadata.jsonl.
        """
        known_fields = {
            "chunk_id", "doc_id", "fuente", "formato",
            "fenomeno", "posicion", "num_tokens", "texto", "faiss_id",
        }
        extra = {k: v for k, v in record.items() if k not in known_fields}
        return cls(
            chunk_id   = record["chunk_id"],
            doc_id     = record["doc_id"],
            fuente     = record["fuente"],
            formato    = record["formato"],
            fenomeno   = int(record["fenomeno"]),
            posicion   = int(record["posicion"]),
            num_tokens = int(record["num_tokens"]),
            texto      = record["texto"],
            faiss_id   = int(record.get("faiss_id", -1)),
            metadata   = extra,
        )

    def __repr__(self) -> str:
        snippet = self.texto[:60].replace("\n", " ")
        return (
            f"Chunk(id={self.chunk_id!r}, doc={self.doc_id!r}, "
            f"pos={self.posicion}, tokens={self.num_tokens}, "
            f"preview={snippet!r})"
        )
