"""
Modelo de consulta para AD_ASTRA — CODEFEST 2026.

Representa una consulta del dataset de evaluación (q001–q050) y sus
parámetros de recuperación.

Ref: Sección 10.1 — Dataset de evaluación.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Query:
    """
    Consulta del conjunto de evaluación del CODEFEST.

    Attributes:
        query_id:        Identificador de la consulta ('q001'–'q050').
        text:            Texto de la consulta en lenguaje natural.
        top_k_fragments: Número de fragmentos a recuperar (spec exige 10).
        top_k_documents: Número de documentos a devolver (spec exige 3).
        fenomeno:        Fenómeno temático esperado (1, 2 o 3). None = sin filtro.
        idioma:          Idioma de la consulta ('es', 'en', 'pt'). None = sin filtro.
        filters:         Filtros de metadata adicionales (campo → valor).
        score_threshold: Umbral mínimo de similitud coseno para incluir resultado.
    """
    query_id:        str
    text:            str
    top_k_fragments: int = 10          # obligatorio según spec §9.2
    top_k_documents: int = 3           # obligatorio según spec §9.2
    fenomeno:        int | None = None
    idioma:          str | None = None
    filters:         dict[str, Any] = field(default_factory=dict)
    score_threshold: float = 0.0

    def __post_init__(self) -> None:
        if not self.query_id:
            raise ValueError("query_id no puede estar vacío")
        if not self.text:
            raise ValueError("text (consulta) no puede estar vacío")
        if self.top_k_fragments != 10:
            raise ValueError(
                f"top_k_fragments debe ser 10 según el spec (se recibió {self.top_k_fragments})"
            )
        if self.top_k_documents != 3:
            raise ValueError(
                f"top_k_documents debe ser 3 según el spec (se recibió {self.top_k_documents})"
            )
        if self.fenomeno is not None and self.fenomeno not in (1, 2, 3):
            raise ValueError(f"fenomeno debe ser 1, 2 o 3; se recibió {self.fenomeno}")

    def __repr__(self) -> str:
        snippet = self.text[:60]
        return f"Query(id={self.query_id!r}, text={snippet!r})"
