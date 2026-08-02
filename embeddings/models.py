"""
Definición de modelos de embedding disponibles en AD_ASTRA.

Centraliza los parámetros de cada modelo (nombre, dimensión, proveedor)
para que el resto del sistema no tenga constantes hardcodeadas.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EmbeddingProvider(str, Enum):
    OPENAI = "openai"
    SENTENCE_TRANSFORMERS = "sentence_transformers"
    COHERE = "cohere"


@dataclass(frozen=True)
class EmbeddingModel:
    """
    Descripción de un modelo de embedding.

    Attributes:
        name:       Identificador del modelo tal como lo espera el proveedor.
        provider:   Proveedor del modelo.
        dimensions: Dimensión del vector de salida.
        max_tokens: Tokens máximos de entrada soportados por el modelo.
    """
    name: str
    provider: EmbeddingProvider
    dimensions: int
    max_tokens: int


# ------------------------------------------------------------------
# Catálogo de modelos disponibles
# ------------------------------------------------------------------

MODELS: dict[str, EmbeddingModel] = {
    # OpenAI
    "text-embedding-ada-002": EmbeddingModel(
        name="text-embedding-ada-002",
        provider=EmbeddingProvider.OPENAI,
        dimensions=1536,
        max_tokens=8191,
    ),
    "text-embedding-3-small": EmbeddingModel(
        name="text-embedding-3-small",
        provider=EmbeddingProvider.OPENAI,
        dimensions=1536,
        max_tokens=8191,
    ),
    "text-embedding-3-large": EmbeddingModel(
        name="text-embedding-3-large",
        provider=EmbeddingProvider.OPENAI,
        dimensions=3072,
        max_tokens=8191,
    ),
    # Sentence Transformers (locales)
    "all-MiniLM-L6-v2": EmbeddingModel(
        name="all-MiniLM-L6-v2",
        provider=EmbeddingProvider.SENTENCE_TRANSFORMERS,
        dimensions=384,
        max_tokens=256,
    ),
    "paraphrase-multilingual-MiniLM-L12-v2": EmbeddingModel(
        name="paraphrase-multilingual-MiniLM-L12-v2",
        provider=EmbeddingProvider.SENTENCE_TRANSFORMERS,
        dimensions=384,
        max_tokens=128,
    ),
    "multi-qa-mpnet-base-dot-v1": EmbeddingModel(
        name="multi-qa-mpnet-base-dot-v1",
        provider=EmbeddingProvider.SENTENCE_TRANSFORMERS,
        dimensions=768,
        max_tokens=512,
    ),
    # Cohere
    "embed-multilingual-v3.0": EmbeddingModel(
        name="embed-multilingual-v3.0",
        provider=EmbeddingProvider.COHERE,
        dimensions=1024,
        max_tokens=512,
    ),
}


def get_embedding_model(name: str) -> EmbeddingModel:
    """
    Devuelve el EmbeddingModel correspondiente al nombre dado.

    Args:
        name: Clave del modelo en el catálogo MODELS.

    Returns:
        EmbeddingModel con los parámetros del modelo.

    Raises:
        ValueError: Si el nombre no está en el catálogo.
    """
    model = MODELS.get(name)
    if model is None:
        available = ", ".join(MODELS.keys())
        raise ValueError(f"Modelo '{name}' no encontrado. Disponibles: {available}")
    return model
