"""
Encoder de embeddings para AD_ASTRA — CODEFEST 2026.

Usa exclusivamente modelos encoder de HuggingFace a través de
sentence-transformers. Los modelos generativos (GPT, LLaMA, etc.)
están prohibidos por el spec (Sección 8.3).

Funcionalidades:
- Normalización L2 automática (para similitud coseno con IndexFlatIP)
- Prefijos query/documento según el modelo (multilingual-e5)
- Batching con barra de progreso opcional
- Encode de textos, Documents y Chunks
"""
from __future__ import annotations

import numpy as np

from config.settings import (
    EMBEDDING_MODEL,
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_NORMALIZE,
)
from core.document import Document
from embeddings.models import EmbeddingModel, get_embedding_model


class Encoder:
    """
    Genera embeddings usando un modelo SentenceTransformer de HuggingFace.

    Args:
        model_name:  Nombre del modelo en el catálogo (e.g. 'BAAI/bge-m3').
        batch_size:  Textos por lote durante la inferencia.
        normalize:   Si True, normaliza vectores a norma unitaria (L2).
                     Requerido para similitud coseno con IndexFlatIP.
        device:      'cpu', 'cuda' o 'mps'. None = detección automática.
        show_progress: Muestra barra de progreso en encode().
    """

    def __init__(
        self,
        model_name:    str  = EMBEDDING_MODEL,
        batch_size:    int  = EMBEDDING_BATCH_SIZE,
        normalize:     bool = EMBEDDING_NORMALIZE,
        device:        str | None = None,
        show_progress: bool = False,
    ) -> None:
        self.model_info:    EmbeddingModel = get_embedding_model(model_name)
        self.batch_size:    int  = batch_size
        self.normalize:     bool = normalize
        self.show_progress: bool = show_progress
        self._model = self._load_model(device)

    # ------------------------------------------------------------------
    # Carga del modelo
    # ------------------------------------------------------------------

    def _load_model(self, device: str | None):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                "Instala sentence-transformers: pip install sentence-transformers"
            ) from exc

        print(f"[Encoder] Cargando modelo: {self.model_info.name}")
        model = SentenceTransformer(self.model_info.name, device=device)
        print(f"[Encoder] Modelo listo — dimensiones: {self.dimensions}")
        return model

    # ------------------------------------------------------------------
    # Prefijos según modelo (multilingual-e5 los requiere)
    # ------------------------------------------------------------------

    def _apply_query_prefix(self, text: str) -> str:
        prefix = self.model_info.query_prefix
        return f"{prefix}{text}" if prefix else text

    def _apply_doc_prefix(self, text: str) -> str:
        prefix = self.model_info.doc_prefix
        return f"{prefix}{text}" if prefix else text

    # ------------------------------------------------------------------
    # Normalización L2
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize(vectors: np.ndarray) -> np.ndarray:
        """Normaliza cada vector a norma unitaria (L2)."""
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)   # evitar división por cero
        return vectors / norms

    # ------------------------------------------------------------------
    # API pública — textos
    # ------------------------------------------------------------------

    def encode(self, texts: list[str], is_query: bool = False) -> np.ndarray:
        """
        Genera embeddings para una lista de textos.

        Args:
            texts:    Lista de cadenas a vectorizar.
            is_query: Si True, aplica el prefijo de consulta del modelo.
                      Si False, aplica el prefijo de documento.

        Returns:
            Array numpy float32 de shape (len(texts), dimensions).
            Si normalize=True, cada vector tiene norma unitaria.
        """
        if not texts:
            return np.empty((0, self.dimensions), dtype=np.float32)

        # Aplicar prefijo según rol
        if is_query:
            processed = [self._apply_query_prefix(t) for t in texts]
        else:
            processed = [self._apply_doc_prefix(t) for t in texts]

        vectors = self._model.encode(
            processed,
            batch_size        = self.batch_size,
            show_progress_bar = self.show_progress,
            convert_to_numpy  = True,
        ).astype(np.float32)

        if self.normalize:
            vectors = self._normalize(vectors)

        return vectors

    def encode_query(self, query: str) -> np.ndarray:
        """
        Vectoriza una consulta de usuario.

        Aplica el prefijo de query del modelo. Retorna vector 1D
        de shape (dimensions,) listo para buscar en FAISS.

        Ref: Sección 8.1 del spec — mismo encoder para indexar y recuperar.
        """
        return self.encode([query], is_query=True)[0]

    # ------------------------------------------------------------------
    # API pública — Documents
    # ------------------------------------------------------------------

    def encode_document(self, document: Document) -> np.ndarray:
        """Vectoriza el contenido de un Document. Retorna vector 1D."""
        return self.encode([document.content], is_query=False)[0]

    def encode_documents(self, documents: list[Document]) -> np.ndarray:
        """
        Vectoriza una lista de Documents.

        Returns:
            Array numpy de shape (len(documents), dimensions).
        """
        texts = [doc.content for doc in documents]
        return self.encode(texts, is_query=False)

    def encode_chunks(self, chunks) -> np.ndarray:
        """
        Vectoriza una lista de Chunk (core.chunk.Chunk).

        Usa el campo 'texto' del chunk (texto original sin modificar).

        Returns:
            Array numpy de shape (len(chunks), dimensions).
        """
        texts = []

        for i, c in enumerate(chunks):

            print(
                f"Chunk {i}: "
                f"{type(c)}"
            )

            print(
                f"texto type: "
                f"{type(c.texto)}"
            )

            if not isinstance(c.texto, str):

                print("VALOR:")
                print(c.texto)

                raise TypeError(
                    f"Chunk {i} tiene texto inválido"
                )

            texts.append(c.texto)

        return self.encode(
            texts,
            is_query=False,
        )

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    @property
    def dimensions(self) -> int:
        """Dimensión del vector de salida."""
        return self.model_info.dimensions

    @property
    def max_tokens(self) -> int:
        """Tokens máximos de entrada del modelo."""
        return self.model_info.max_tokens

    @property
    def model_name(self) -> str:
        """Nombre del modelo."""
        return self.model_info.name

    def __repr__(self) -> str:
        return (
            f"Encoder(model={self.model_name!r}, "
            f"dims={self.dimensions}, "
            f"normalize={self.normalize})"
        )
