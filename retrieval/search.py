"""
Búsqueda vectorial sobre el índice FAISS para AD_ASTRA.
"""
from __future__ import annotations

import numpy as np

from core.document import Document
from embeddings.encoder import Encoder
from retrieval.filters import MetadataFilter
from vectorstore.faiss_manager import FAISSManager
from vectorstore.metadata_store import MetadataStore


class SearchResult:
    """
    Contenedor de un resultado de búsqueda.

    Attributes:
        document: Document recuperado.
        score:    Puntuación de similitud (mayor = más similar).
        rank:     Posición en la lista de resultados (1-indexed).
    """

    def __init__(self, document: Document, score: float, rank: int) -> None:
        self.document = document
        self.score = score
        self.rank = rank

    def __repr__(self) -> str:
        snippet = self.document.content[:60].replace("\n", " ")
        return f"SearchResult(rank={self.rank}, score={self.score:.4f}, preview={snippet!r})"


class VectorSearch:
    """
    Realiza búsquedas semánticas sobre un índice FAISS + MetadataStore.

    Args:
        faiss_manager:    Índice FAISS con los vectores.
        metadata_store:   Store con los Documents asociados.
        encoder:          Encoder para vectorizar la query.
        default_k:        Número de resultados por defecto.
    """

    def __init__(
        self,
        faiss_manager: FAISSManager,
        metadata_store: MetadataStore,
        encoder: Encoder,
        default_k: int = 5,
    ) -> None:
        self.faiss = faiss_manager
        self.metadata = metadata_store
        self.encoder = encoder
        self.default_k = default_k

    # ------------------------------------------------------------------
    # Búsqueda principal
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        k: int | None = None,
        filters: MetadataFilter | None = None,
        score_threshold: float | None = None,
    ) -> list[SearchResult]:
        """
        Busca los documentos más similares a la query.

        Args:
            query:           Texto de consulta.
            k:               Número de resultados. Usa default_k si es None.
            filters:         Filtro de metadatos aplicado post-búsqueda.
            score_threshold: Puntuación mínima para incluir un resultado.

        Returns:
            Lista de SearchResult ordenados por score descendente.
        """
        top_k = k or self.default_k

        # Codificar query
        query_vector = self.encoder.encode([query])[0].reshape(1, -1)

        # Recuperar más resultados si hay filtros (pre-fetch)
        fetch_k = top_k * 3 if filters else top_k
        distances, indices = self.faiss.search(query_vector, k=fetch_k)

        results: list[SearchResult] = []
        flat_indices = indices[0].tolist()
        flat_distances = distances[0].tolist()

        for rank, (idx, dist) in enumerate(zip(flat_indices, flat_distances), start=1):
            if idx == -1:
                continue

            doc = self.metadata.get_documents([idx])[0]

            # Aplicar filtro de metadatos
            if filters and not filters.matches(doc):
                continue

            # Normalizar score: para flat_ip ya es similitud; para flat_l2 invertimos
            score = float(dist) if self.faiss.index_type == "flat_ip" else float(1 / (1 + dist))

            if score_threshold is not None and score < score_threshold:
                continue

            results.append(SearchResult(document=doc, score=score, rank=rank))

            if len(results) >= top_k:
                break

        # Re-rankear por score
        results.sort(key=lambda r: r.score, reverse=True)
        for i, r in enumerate(results, start=1):
            r.rank = i

        return results

    def search_by_vector(
        self,
        vector: np.ndarray,
        k: int | None = None,
    ) -> list[SearchResult]:
        """
        Búsqueda directamente por vector (sin encoding).

        Args:
            vector: Array numpy de shape (dimensions,).
            k:      Número de resultados.

        Returns:
            Lista de SearchResult.
        """
        top_k = k or self.default_k
        distances, indices = self.faiss.search(vector, k=top_k)

        results: list[SearchResult] = []
        for rank, (idx, dist) in enumerate(zip(indices[0].tolist(), distances[0].tolist()), start=1):
            if idx == -1:
                continue
            doc = self.metadata.get_documents([idx])[0]
            score = float(dist) if self.faiss.index_type == "flat_ip" else float(1 / (1 + dist))
            results.append(SearchResult(document=doc, score=score, rank=rank))

        return results
