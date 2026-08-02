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

    Carga un índice pre-construido y responde queries.

    Args:
        index_path:       Ruta al archivo faiss.index.
        metadata_path:    Ruta al archivo metadata.json.
        embedding_model:  Modelo de embedding a usar para la query.
        api_key:          API key del proveedor. None = variable de entorno.
        default_k:        Número de resultados por defecto.
        index_type:       Tipo de índice FAISS ('flat_ip', 'flat_l2', 'ivf_flat').
    """

    def __init__(
        self,
        index_path: Union[str, Path, None] = None,
        metadata_path: Union[str, Path, None] = None,
        embedding_model: str = EMBEDDING_MODEL,
        api_key: str | None = None,
        default_k: int = 5,
        index_type: str = "flat_ip",
    ) -> None:
        base = Path(VECTORSTORE_PATH)
        self._index_path    = Path(index_path)    if index_path    else base / "faiss.index"
        self._metadata_path = Path(metadata_path) if metadata_path else base / "metadata.json"

        self.encoder = Encoder(
            model_name=embedding_model,
            batch_size=EMBEDDING_BATCH_SIZE,
            api_key=api_key,
        )

        self.faiss_mgr    = FAISSManager.load(
            self._index_path,
            dimensions=self.encoder.dimensions,
            index_type=index_type,
        )
        self.metadata_store = MetadataStore.load(self._metadata_path)

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
        Recupera los documentos más relevantes para la consulta.

        Args:
            text:            Consulta en lenguaje natural.
            k:               Número de resultados. None = default_k.
            filters:         Filtro de metadatos (MetadataFilter).
            score_threshold: Score mínimo para incluir un resultado.

        Returns:
            Lista de SearchResult ordenados por score descendente.
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
        Búsqueda vectorial + fusión RRF con resultados adicionales.

        Útil para combinar búsqueda densa (vectorial) con esparsa (BM25).

        Args:
            text:          Consulta en lenguaje natural.
            extra_results: Listas de resultados de otros retrievers.
            k:             Número de resultados finales.
            rrf_k:         Constante de suavizado RRF.
            weights:       Pesos por lista para RRF ponderado.

        Returns:
            Lista fusionada de SearchResult.
        """
        vector_results = self.query(text, k=k * 3)
        all_lists = [vector_results] + (extra_results or [])

        fuser = ReciprocalRankFusion(k=rrf_k)
        if weights:
            return fuser.fuse_with_scores(all_lists, weights=weights, top_k=k)
        return fuser.fuse(all_lists, top_k=k)

    def get_context_string(
        self,
        text: str,
        k: int | None = None,
        separator: str = "\n\n---\n\n",
        filters: MetadataFilter | None = None,
    ) -> str:
        """
        Recupera documentos y los concatena como string listo para usar
        en un prompt de LLM.

        Args:
            text:      Consulta.
            k:         Número de documentos.
            separator: Separador entre fragmentos.
            filters:   Filtro de metadatos.

        Returns:
            String con los fragmentos de contexto concatenados.
        """
        results = self.query(text, k=k, filters=filters)
        return separator.join(r.document.content for r in results)
