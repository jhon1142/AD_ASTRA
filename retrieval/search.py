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
        document: Documento o fragmento recuperado.
        score: Puntuación de similitud.
        rank: Posición del resultado, comenzando en 1.
    """

    def __init__(
        self,
        document: Document,
        score: float,
        rank: int,
    ) -> None:
        self.document = document
        self.score = score
        self.rank = rank

    def __repr__(self) -> str:
        snippet = self.document.content[:60].replace("\n", " ")

        return (
            f"SearchResult("
            f"rank={self.rank}, "
            f"score={self.score:.4f}, "
            f"preview={snippet!r}"
            f")"
        )


class VectorSearch:
    """
    Realiza búsquedas semánticas sobre un índice FAISS
    asociado a un MetadataStore.

    Args:
        faiss_manager: Índice FAISS.
        metadata_store: Metadata asociada a los vectores.
        encoder: Encoder utilizado para vectorizar consultas.
        default_k: Número de resultados por defecto.
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
    # Utilidades internas
    # ------------------------------------------------------------------

    def _distance_to_score(
        self,
        distance: float,
    ) -> float:
        """
        Convierte la distancia devuelta por FAISS en un score
        donde un valor mayor representa mayor similitud.
        """

        if self.faiss.index_type == "flat_ip":
            return float(distance)

        return float(
            1.0 / (1.0 + max(float(distance), 0.0))
        )

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
        Busca los fragmentos más similares a una consulta.

        Args:
            query: Texto de consulta.
            k: Número de resultados finales.
            filters: Filtro opcional de metadatos.
            score_threshold: Score mínimo permitido.

        Returns:
            Lista de SearchResult ordenada por relevancia.
        """

        if not query or not query.strip():
            return []

        top_k = k if k is not None else self.default_k

        if top_k <= 0:
            return []

        # --------------------------------------------------------------
        # Vectorizar la consulta
        #
        # Se utiliza encode_query() en lugar de encode() porque algunos
        # encoders aplican tratamiento o prefijos específicos a queries.
        # --------------------------------------------------------------

        query_vector = self.encoder.encode_query(
            query.strip()
        )

        query_vector = np.asarray(
            query_vector,
            dtype=np.float32,
        ).reshape(1, -1)

        # --------------------------------------------------------------
        # Recuperación de candidatos
        #
        # Recuperamos más candidatos que resultados finales para evitar
        # limitar demasiado pronto el ranking y permitir filtros posteriores.
        # --------------------------------------------------------------

        candidate_k = max(
            top_k * 5,
            50,
        )

        distances, indices = self.faiss.search(
            query_vector,
            k=candidate_k,
        )

        results: list[SearchResult] = []

        flat_indices = indices[0].tolist()
        flat_distances = distances[0].tolist()

        for idx, distance in zip(
            flat_indices,
            flat_distances,
        ):

            # FAISS devuelve -1 cuando no existen más resultados.
            if idx == -1:
                continue

            documents = self.metadata.get_documents(
                [idx]
            )

            if not documents:
                continue

            document = documents[0]

            # ----------------------------------------------------------
            # Filtros de metadata
            # ----------------------------------------------------------

            if filters is not None:
                if not filters.matches(document):
                    continue

            # ----------------------------------------------------------
            # Conversión del valor FAISS a score de relevancia
            # ----------------------------------------------------------

            score = self._distance_to_score(
                distance
            )

            if (
                score_threshold is not None
                and score < score_threshold
            ):
                continue

            results.append(
                SearchResult(
                    document=document,
                    score=score,
                    rank=0,
                )
            )

        # --------------------------------------------------------------
        # Orden final
        # --------------------------------------------------------------

        results.sort(
            key=lambda result: result.score,
            reverse=True,
        )

        results = results[:top_k]

        for rank, result in enumerate(
            results,
            start=1,
        ):
            result.rank = rank

        return results

    # ------------------------------------------------------------------
    # Búsqueda directa por vector
    # ------------------------------------------------------------------

    def search_by_vector(
        self,
        vector: np.ndarray,
        k: int | None = None,
    ) -> list[SearchResult]:
        """
        Ejecuta una búsqueda usando directamente un vector.

        Args:
            vector: Vector numpy de embeddings.
            k: Número de resultados.

        Returns:
            Lista de SearchResult.
        """

        top_k = k if k is not None else self.default_k

        if top_k <= 0:
            return []

        vector = np.asarray(
            vector,
            dtype=np.float32,
        )

        if vector.ndim == 1:
            vector = vector.reshape(1, -1)

        elif vector.ndim != 2:
            raise ValueError(
                "El vector debe tener una o dos dimensiones."
            )

        distances, indices = self.faiss.search(
            vector,
            k=top_k,
        )

        results: list[SearchResult] = []

        flat_indices = indices[0].tolist()
        flat_distances = distances[0].tolist()

        for idx, distance in zip(
            flat_indices,
            flat_distances,
        ):

            if idx == -1:
                continue

            documents = self.metadata.get_documents(
                [idx]
            )

            if not documents:
                continue

            document = documents[0]

            score = self._distance_to_score(
                distance
            )

            results.append(
                SearchResult(
                    document=document,
                    score=score,
                    rank=0,
                )
            )

        results.sort(
            key=lambda result: result.score,
            reverse=True,
        )

        for rank, result in enumerate(
            results,
            start=1,
        ):
            result.rank = rank

        return results