"""
Pipeline de recuperación de documentos para AD_ASTRA.

Carga el índice FAISS + MetadataStore y expone una interfaz simple
para responder consultas en lenguaje natural.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

from config.settings import (
    EMBEDDING_MODEL,
    EMBEDDING_BATCH_SIZE,
    VECTORSTORE_PATH,
)
from embeddings.encoder import Encoder
from retrieval.filters import MetadataFilter
from retrieval.fusion import ReciprocalRankFusion
from retrieval.search import SearchResult, VectorSearch
from vectorstore.faiss_manager import FAISSManager
from vectorstore.metadata_store import MetadataStore


class Retriever:
    """
    Punto de entrada para la recuperación de documentos.

    Carga un índice FAISS preconstruido junto con su metadata
    y permite ejecutar consultas vectoriales.

    Args:
        index_path: Ruta al archivo index.faiss.
        metadata_path: Ruta al archivo metadata.jsonl.
        embedding_model: Modelo de embeddings usado para las consultas.
        default_k: Número de resultados por defecto.
        index_type: Tipo de índice FAISS
                    ('flat_ip', 'flat_l2', 'ivf_flat').
    """

    def __init__(
        self,
        index_path: Union[str, Path, None] = None,
        metadata_path: Union[str, Path, None] = None,
        embedding_model: str = EMBEDDING_MODEL,
        default_k: int = 5,
        index_type: str = "flat_ip",
    ) -> None:

        base = Path(VECTORSTORE_PATH)

        self._index_path = (
            Path(index_path)
            if index_path
            else base / "index.faiss"
        )

        self._metadata_path = (
            Path(metadata_path)
            if metadata_path
            else base / "metadata.jsonl"
        )

        self.encoder = Encoder(
            model_name=embedding_model,
            batch_size=EMBEDDING_BATCH_SIZE,
        )

        self.faiss_mgr = FAISSManager.load(
            self._index_path,
            dimensions=self.encoder.dimensions,
            index_type=index_type,
        )

        self.metadata_store = MetadataStore.load(
            self._metadata_path
        )

        self.search_engine = VectorSearch(
            faiss_manager=self.faiss_mgr,
            metadata_store=self.metadata_store,
            encoder=self.encoder,
            default_k=default_k,
        )

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def query(
        self,
        text: str,
        k: int | None = None,
        filters: MetadataFilter | None = None,
        score_threshold: float | None = None,
    ) -> list[SearchResult]:
        """
        Recupera los fragmentos más relevantes para una consulta.

        Args:
            text: Consulta en lenguaje natural.
            k: Número de resultados. None utiliza default_k.
            filters: Filtros opcionales sobre los metadatos.
            score_threshold: Score mínimo requerido.

        Returns:
            Lista de SearchResult ordenada por relevancia.
        """

        return self.search_engine.search(
            query=text,
            k=k,
            filters=filters,
            score_threshold=score_threshold,
        )

    def query_and_fuse(
        self,
        text: str,
        extra_results: list[list[SearchResult]] | None = None,
        k: int = 5,
        rrf_k: int = 60,
        weights: list[float] | None = None,
    ) -> list[SearchResult]:
        """
        Ejecuta búsqueda vectorial y permite combinar resultados
        mediante Reciprocal Rank Fusion (RRF).

        Args:
            text: Consulta en lenguaje natural.
            extra_results: Resultados adicionales de otros índices.
            k: Número de resultados finales.
            rrf_k: Constante utilizada por RRF.
            weights: Pesos opcionales para cada lista de resultados.

        Returns:
            Lista fusionada de SearchResult.
        """

        vector_results = self.query(
            text,
            k=k * 3,
        )

        all_lists = [
            vector_results,
            *(extra_results or []),
        ]

        fuser = ReciprocalRankFusion(
            k=rrf_k
        )

        if weights:
            return fuser.fuse_with_scores(
                all_lists,
                weights=weights,
                top_k=k,
            )

        return fuser.fuse(
            all_lists,
            top_k=k,
        )

    def get_context_string(
        self,
        text: str,
        k: int | None = None,
        separator: str = "\n\n---\n\n",
        filters: MetadataFilter | None = None,
    ) -> str:
        """
        Recupera fragmentos y los concatena en una única cadena.

        Este método no utiliza modelos generativos ni modifica
        el contenido recuperado.

        Args:
            text: Consulta.
            k: Número de fragmentos.
            separator: Separador entre fragmentos.
            filters: Filtros opcionales de metadata.

        Returns:
            Texto concatenado de los fragmentos recuperados.
        """

        results = self.query(
            text,
            k=k,
            filters=filters,
        )

        return separator.join(
            result.document.content
            for result in results
        )