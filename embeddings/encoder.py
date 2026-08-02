"""
Encoder unificado de embeddings para AD_ASTRA.

Soporta tres proveedores: OpenAI, Sentence Transformers y Cohere.
La interfaz es la misma independientemente del proveedor.
"""
from __future__ import annotations

import numpy as np

from config.settings import EMBEDDING_MODEL, EMBEDDING_BATCH_SIZE
from core.document import Document
from embeddings.models import EmbeddingModel, EmbeddingProvider, get_embedding_model


class Encoder:
    """
    Genera embeddings para textos y documentos.

    Args:
        model_name:  Nombre del modelo (debe estar en embeddings.models.MODELS).
        batch_size:  Número de textos enviados por llamada a la API.
        api_key:     API key del proveedor. Si es None, se lee de las
                     variables de entorno (OPENAI_API_KEY, COHERE_API_KEY).
    """

    def __init__(
        self,
        model_name: str = EMBEDDING_MODEL,
        batch_size: int = EMBEDDING_BATCH_SIZE,
        api_key: str | None = None,
    ) -> None:
        self.model: EmbeddingModel = get_embedding_model(model_name)
        self.batch_size = batch_size
        self.api_key = api_key
        self._client = self._build_client()

    # ------------------------------------------------------------------
    # Inicialización del cliente según proveedor
    # ------------------------------------------------------------------

    def _build_client(self):
        provider = self.model.provider

        if provider == EmbeddingProvider.OPENAI:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise ImportError("Instala 'openai': pip install openai") from exc
            return OpenAI(api_key=self.api_key) if self.api_key else OpenAI()

        if provider == EmbeddingProvider.SENTENCE_TRANSFORMERS:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise ImportError(
                    "Instala 'sentence-transformers': pip install sentence-transformers"
                ) from exc
            return SentenceTransformer(self.model.name)

        if provider == EmbeddingProvider.COHERE:
            try:
                import cohere
            except ImportError as exc:
                raise ImportError("Instala 'cohere': pip install cohere") from exc
            return cohere.Client(self.api_key) if self.api_key else cohere.Client()

        raise ValueError(f"Proveedor no soportado: {provider}")

    # ------------------------------------------------------------------
    # Métodos de embedding
    # ------------------------------------------------------------------

    def _embed_openai(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(
            input=texts,
            model=self.model.name,
        )
        return [item.embedding for item in response.data]

    def _embed_sentence_transformers(self, texts: list[str]) -> list[list[float]]:
        vectors = self._client.encode(texts, batch_size=self.batch_size, show_progress_bar=False)
        return vectors.tolist()

    def _embed_cohere(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embed(
            texts=texts,
            model=self.model.name,
            input_type="search_document",
        )
        return response.embeddings

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        provider = self.model.provider
        if provider == EmbeddingProvider.OPENAI:
            return self._embed_openai(texts)
        if provider == EmbeddingProvider.SENTENCE_TRANSFORMERS:
            return self._embed_sentence_transformers(texts)
        if provider == EmbeddingProvider.COHERE:
            return self._embed_cohere(texts)
        raise ValueError(f"Proveedor no soportado: {provider}")

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def encode(self, texts: list[str]) -> np.ndarray:
        """
        Genera embeddings para una lista de textos.

        Args:
            texts: Lista de cadenas a vectorizar.

        Returns:
            Array numpy de shape (len(texts), dimensions).
        """
        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            all_embeddings.extend(self._embed_batch(batch))

        return np.array(all_embeddings, dtype=np.float32)

    def encode_document(self, document: Document) -> np.ndarray:
        """Genera el embedding del contenido de un Document."""
        return self.encode([document.content])[0]

    def encode_documents(self, documents: list[Document]) -> np.ndarray:
        """
        Genera embeddings para una lista de Documents.

        Returns:
            Array numpy de shape (len(documents), dimensions).
        """
        texts = [doc.content for doc in documents]
        return self.encode(texts)

    @property
    def dimensions(self) -> int:
        """Dimensión del vector de salida del modelo."""
        return self.model.dimensions
