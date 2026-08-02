"""
Modelos de resultado para AD_ASTRA — CODEFEST 2026.

Define las estructuras de salida que el sistema debe producir por consulta,
alineadas exactamente con el esquema JSON de entrega (Sección 9.3 del spec).

Entregable: resultados.jsonl — 50 líneas, una por consulta.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class FragmentResult:
    """
    Un fragmento recuperado para una consulta.

    Campos requeridos por el spec (Tabla 2):
        rank:     Posición en el ranking (1–10).
        chunk_id: Identificador del chunk recuperado del índice.
        doc_id:   Identificador del documento de origen del fragmento.
        text:     Texto del fragmento (≤ 250 palabras).

    Attribute adicional (interno, no se serializa):
        score:    Puntuación de similitud coseno con la consulta.
    """
    rank:     int
    chunk_id: str
    doc_id:   str
    text:     str
    score:    float = 0.0    # no se incluye en el JSON de entrega

    def __post_init__(self) -> None:
        if not (1 <= self.rank <= 10):
            raise ValueError(f"rank de fragmento debe estar entre 1 y 10; se recibió {self.rank}")
        if self.word_count > 250:
            raise ValueError(
                f"El fragmento rank={self.rank} supera las 250 palabras ({self.word_count}). "
                "Debe truncarse antes de crear FragmentResult."
            )

    @property
    def word_count(self) -> int:
        return len(self.text.split())

    def to_dict(self) -> dict:
        """Serializa al formato del spec (sin el campo score)."""
        return {
            "rank":     self.rank,
            "chunk_id": self.chunk_id,
            "doc_id":   self.doc_id,
            "text":     self.text,
        }


@dataclass
class DocumentResult:
    """
    Un documento recuperado para una consulta.

    Campos requeridos por el spec (Tabla 2):
        rank:   Posición en el ranking (1–3).
        doc_id: Identificador del documento.

    Attribute adicional (interno, no se serializa):
        score:  Puntuación agregada del documento.
    """
    rank:   int
    doc_id: str
    score:  float = 0.0    # no se incluye en el JSON de entrega

    def __post_init__(self) -> None:
        if not (1 <= self.rank <= 3):
            raise ValueError(f"rank de documento debe estar entre 1 y 3; se recibió {self.rank}")

    def to_dict(self) -> dict:
        """Serializa al formato del spec (sin el campo score)."""
        return {"rank": self.rank, "doc_id": self.doc_id}


@dataclass
class QueryResult:
    """
    Resultado completo para una consulta del dataset de evaluación.

    Debe contener exactamente:
        - 3 DocumentResult (spec §9.2)
        - 10 FragmentResult con texto ≤ 250 palabras cada uno (spec §9.2)

    Ref: Sección 9.3 — Formato JSON Lines de entrega.
    """
    query_id:  str
    documents: list[DocumentResult] = field(default_factory=list)
    fragments: list[FragmentResult] = field(default_factory=list)

    def validate(self) -> None:
        """
        Valida que el resultado cumpla estrictamente el esquema del spec.
        Lanza ValueError con descripción detallada del problema.
        """
        if len(self.documents) != 3:
            raise ValueError(
                f"Se requieren exactamente 3 documentos; hay {len(self.documents)} "
                f"(query_id={self.query_id!r})"
            )
        if len(self.fragments) != 10:
            raise ValueError(
                f"Se requieren exactamente 10 fragmentos; hay {len(self.fragments)} "
                f"(query_id={self.query_id!r})"
            )
        for fr in self.fragments:
            if fr.word_count > 250:
                raise ValueError(
                    f"Fragmento rank={fr.rank} supera 250 palabras ({fr.word_count}) "
                    f"en query_id={self.query_id!r}"
                )
        doc_ranks = [d.rank for d in self.documents]
        if sorted(doc_ranks) != [1, 2, 3]:
            raise ValueError(f"Los ranks de documentos deben ser [1,2,3]; se recibió {doc_ranks}")
        frag_ranks = sorted(f.rank for f in self.fragments)
        if frag_ranks != list(range(1, 11)):
            raise ValueError(f"Los ranks de fragmentos deben ser [1..10]; se recibió {frag_ranks}")

    def to_dict(self) -> dict:
        """Serializa al esquema JSON del spec (Sección 9.3.1)."""
        return {
            "query_id":  self.query_id,
            "documents": [d.to_dict() for d in sorted(self.documents, key=lambda d: d.rank)],
            "fragments": [f.to_dict() for f in sorted(self.fragments, key=lambda f: f.rank)],
        }

    def to_jsonl_line(self) -> str:
        """Genera una línea del archivo resultados.jsonl."""
        self.validate()
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def __repr__(self) -> str:
        return (
            f"QueryResult(id={self.query_id!r}, "
            f"docs={len(self.documents)}, frags={len(self.fragments)})"
        )
