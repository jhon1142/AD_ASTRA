"""
Filtros de metadatos para resultados de recuperación en AD_ASTRA.

Permite filtrar documentos recuperados basándose en sus metadatos
antes o después de la búsqueda vectorial.
"""
from __future__ import annotations

import re
from enum import Enum
from typing import Any

from core.document import Document


class FilterOp(str, Enum):
    """Operadores de comparación disponibles."""
    EQ = "eq"           # igual
    NEQ = "neq"         # diferente
    GT = "gt"           # mayor que
    GTE = "gte"         # mayor o igual
    LT = "lt"           # menor que
    LTE = "lte"         # menor o igual
    IN = "in"           # valor en lista
    NOT_IN = "not_in"   # valor no en lista
    CONTAINS = "contains"       # string contiene substring
    REGEX = "regex"             # string cumple regex
    EXISTS = "exists"           # campo existe en metadatos


class FilterCondition:
    """
    Una condición de filtro individual.

    Args:
        field:    Clave del metadato a evaluar.
        op:       Operador de comparación (FilterOp).
        value:    Valor de referencia para la comparación.
    """

    def __init__(self, field: str, op: FilterOp | str, value: Any = None) -> None:
        self.field = field
        self.op = FilterOp(op)
        self.value = value

    def evaluate(self, document: Document) -> bool:
        """Evalúa la condición contra los metadatos de un Document."""
        meta = document.metadata
        field_value = meta.get(self.field)

        match self.op:
            case FilterOp.EXISTS:
                return self.field in meta
            case FilterOp.EQ:
                return field_value == self.value
            case FilterOp.NEQ:
                return field_value != self.value
            case FilterOp.GT:
                return field_value is not None and field_value > self.value
            case FilterOp.GTE:
                return field_value is not None and field_value >= self.value
            case FilterOp.LT:
                return field_value is not None and field_value < self.value
            case FilterOp.LTE:
                return field_value is not None and field_value <= self.value
            case FilterOp.IN:
                return field_value in self.value
            case FilterOp.NOT_IN:
                return field_value not in self.value
            case FilterOp.CONTAINS:
                return isinstance(field_value, str) and self.value in field_value
            case FilterOp.REGEX:
                return bool(isinstance(field_value, str) and re.search(self.value, field_value))
            case _:
                return False


class MetadataFilter:
    """
    Combina múltiples FilterCondition con lógica AND u OR.

    Args:
        conditions: Lista de FilterCondition.
        logic:      'and' (todas deben cumplirse) o 'or' (al menos una).

    Example:
        >>> f = MetadataFilter([
        ...     FilterCondition("file_type", FilterOp.EQ, "pdf"),
        ...     FilterCondition("page", FilterOp.LTE, 10),
        ... ], logic="and")
        >>> f.matches(doc)
    """

    def __init__(
        self,
        conditions: list[FilterCondition],
        logic: str = "and",
    ) -> None:
        if logic not in ("and", "or"):
            raise ValueError("logic debe ser 'and' o 'or'")
        self.conditions = conditions
        self.logic = logic

    def matches(self, document: Document) -> bool:
        """
        Evalúa si un Document cumple el filtro.

        Returns:
            True si el documento pasa el filtro.
        """
        if not self.conditions:
            return True

        results = [c.evaluate(document) for c in self.conditions]

        return all(results) if self.logic == "and" else any(results)

    def filter(self, documents: list[Document]) -> list[Document]:
        """Filtra una lista de Documents devolviendo solo los que pasan."""
        return [doc for doc in documents if self.matches(doc)]

    # ------------------------------------------------------------------
    # Constructores de conveniencia
    # ------------------------------------------------------------------

    @classmethod
    def by_source(cls, source: str) -> "MetadataFilter":
        """Filtra por fuente exacta."""
        return cls([FilterCondition("source", FilterOp.EQ, source)])

    @classmethod
    def by_file_type(cls, *file_types: str) -> "MetadataFilter":
        """Filtra por tipo de archivo (pdf, html, csv, etc.)."""
        return cls([FilterCondition("file_type", FilterOp.IN, list(file_types))])

    @classmethod
    def by_language(cls, *languages: str) -> "MetadataFilter":
        """Filtra por idioma detectado (es, en, etc.)."""
        return cls([FilterCondition("language", FilterOp.IN, list(languages))])
