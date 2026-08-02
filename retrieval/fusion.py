"""
Fusión de resultados de múltiples retrievers para AD_ASTRA.

Implementa Reciprocal Rank Fusion (RRF), el método estándar para combinar
rankings de búsqueda densa (vectorial) y esparsa (BM25/TF-IDF) u otros.

Referencia: Cormack et al., "Reciprocal Rank Fusion outperforms Condorcet
and individual Rank Learning Methods" (SIGIR 2009).
"""
from __future__ import annotations

from collections import defaultdict

from core.document import Document
from retrieval.search import SearchResult


class ReciprocalRankFusion:
    """
    Combina múltiples listas de SearchResult usando RRF.

    RRF Score = Σ  1 / (k + rank_i)
    donde k es un parámetro de suavizado (típicamente 60).

    Args:
        k:           Constante de suavizado de RRF (default: 60).
        id_field:    Campo de metadatos usado como identificador único de
                     documento. Si es None, usa el contenido como clave.
    """

    def __init__(self, k: int = 60, id_field: str | None = "source") -> None:
        self.k = k
        self.id_field = id_field

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _doc_key(self, result: SearchResult) -> str:
        """Genera una clave única para identificar un documento."""
        if self.id_field:
            key = result.document.metadata.get(self.id_field)
            if key:
                # Incluir chunk_index para distinguir chunks del mismo doc
                chunk = result.document.metadata.get("chunk_index", "")
                return f"{key}::{chunk}"
        return result.document.doc_id or result.document.content[:100]

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def fuse(
        self,
        result_lists: list[list[SearchResult]],
        top_k: int = 10,
    ) -> list[SearchResult]:
        """
        Fusiona múltiples listas de resultados con RRF.

        Args:
            result_lists: Lista de listas de SearchResult. Cada lista
                          proviene de un retriever diferente.
            top_k:        Número máximo de resultados a devolver.

        Returns:
            Lista fusionada de SearchResult ordenada por score RRF descendente.
        """
        rrf_scores: dict[str, float] = defaultdict(float)
        doc_registry: dict[str, Document] = {}

        for result_list in result_lists:
            for result in result_list:
                key = self._doc_key(result)
                rrf_scores[key] += 1.0 / (self.k + result.rank)
                if key not in doc_registry:
                    doc_registry[key] = result.document

        # Ordenar por score RRF
        sorted_keys = sorted(rrf_scores, key=lambda k: rrf_scores[k], reverse=True)[:top_k]

        fused: list[SearchResult] = [
            SearchResult(
                document=doc_registry[key],
                score=rrf_scores[key],
                rank=rank,
            )
            for rank, key in enumerate(sorted_keys, start=1)
        ]

        return fused

    def fuse_with_scores(
        self,
        result_lists: list[list[SearchResult]],
        weights: list[float] | None = None,
        top_k: int = 10,
    ) -> list[SearchResult]:
        """
        Versión ponderada de RRF: aplica un peso por lista de resultados.

        Args:
            result_lists: Lista de listas de SearchResult.
            weights:      Peso para cada lista. Debe tener la misma longitud
                          que result_lists. Si es None, todos los pesos = 1.
            top_k:        Número de resultados a devolver.

        Returns:
            Lista fusionada de SearchResult.
        """
        if weights is None:
            weights = [1.0] * len(result_lists)

        if len(weights) != len(result_lists):
            raise ValueError("weights debe tener la misma longitud que result_lists")

        rrf_scores: dict[str, float] = defaultdict(float)
        doc_registry: dict[str, Document] = {}

        for result_list, weight in zip(result_lists, weights):
            for result in result_list:
                key = self._doc_key(result)
                rrf_scores[key] += weight / (self.k + result.rank)
                if key not in doc_registry:
                    doc_registry[key] = result.document

        sorted_keys = sorted(rrf_scores, key=lambda k: rrf_scores[k], reverse=True)[:top_k]

        return [
            SearchResult(
                document=doc_registry[key],
                score=rrf_scores[key],
                rank=rank,
            )
            for rank, key in enumerate(sorted_keys, start=1)
        ]
