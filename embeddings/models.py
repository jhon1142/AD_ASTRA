"""
Catálogo de modelos de embedding para AD_ASTRA — CODEFEST 2026.

Solo modelos encoder de HuggingFace bajo licencias libres (Apache 2.0 / MIT).
Los modelos generativos (GPT, LLaMA, etc.) están explícitamente excluidos
según la Sección 8.3 del spec.

Criterios de selección (Sección 4.3):
- Soporte multilingüe (es, en, pt)
- Buen rendimiento en MTEB / BEIR
- Licencia libre
- Límite de tokens compatible con la estrategia de chunking
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmbeddingModel:
    """
    Descriptor de un modelo de embedding.

    Attributes:
        name:           Identificador en HuggingFace Hub.
        dimensions:     Dimensión del vector de salida.
        max_tokens:     Tokens máximos de entrada.
        query_prefix:   Prefijo para textos de consulta (algunos modelos lo requieren).
        doc_prefix:     Prefijo para textos de documento.
        normalize:      Si el modelo requiere normalización para similitud coseno.
        license:        Licencia del modelo.
        notes:          Notas sobre el modelo.
    """
    name:         str
    dimensions:   int
    max_tokens:   int
    query_prefix: str = ""
    doc_prefix:   str = ""
    normalize:    bool = True
    license:      str = "Apache 2.0"
    notes:        str = ""


# ── Catálogo de modelos disponibles ──────────────────────────────────────────
# Solo SentenceTransformers / HuggingFace. Sin OpenAI ni Cohere.

MODELS: dict[str, EmbeddingModel] = {

    # ── Recomendado para CODEFEST ─────────────────────────────────────────────
    "BAAI/bge-m3": EmbeddingModel(
        name         = "BAAI/bge-m3",
        dimensions   = 1024,
        max_tokens   = 8192,
        query_prefix = "",   # bge-m3 no requiere prefijo
        doc_prefix   = "",
        normalize    = True,
        license      = "MIT",
        notes        = "Multilingüe (100+ idiomas). Estado del arte en MTEB. "
                       "Soporta es/en/pt nativamente.",
    ),

    # ── Alternativa multilingüe ───────────────────────────────────────────────
    "intfloat/multilingual-e5-large": EmbeddingModel(
        name         = "intfloat/multilingual-e5-large",
        dimensions   = 1024,
        max_tokens   = 512,
        query_prefix = "query: ",
        doc_prefix   = "passage: ",
        normalize    = True,
        license      = "MIT",
        notes        = "Requiere prefijos query:/passage:. Buen rendimiento multilingüe.",
    ),

    "intfloat/multilingual-e5-base": EmbeddingModel(
        name         = "intfloat/multilingual-e5-base",
        dimensions   = 768,
        max_tokens   = 512,
        query_prefix = "query: ",
        doc_prefix   = "passage: ",
        normalize    = True,
        license      = "MIT",
        notes        = "Versión más ligera de multilingual-e5-large.",
    ),

    # ── Modelos livianos para prototipado rápido ──────────────────────────────
    "paraphrase-multilingual-mpnet-base-v2": EmbeddingModel(
        name         = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        dimensions   = 768,
        max_tokens   = 128,
        normalize    = True,
        license      = "Apache 2.0",
        notes        = "Rápido. Límite de 128 tokens — chunks deben ser cortos.",
    ),

    "paraphrase-multilingual-MiniLM-L12-v2": EmbeddingModel(
        name         = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        dimensions   = 384,
        max_tokens   = 128,
        normalize    = True,
        license      = "Apache 2.0",
        notes        = "Muy rápido. Menor calidad que bge-m3 pero útil para pruebas.",
    ),
}


def get_embedding_model(name: str) -> EmbeddingModel:
    """
    Devuelve el EmbeddingModel para el nombre dado.

    Acepta tanto la clave corta ('BAAI/bge-m3') como el nombre completo.

    Raises:
        ValueError: Si el modelo no está en el catálogo.
    """
    model = MODELS.get(name)
    if model is None:
        available = "\n  ".join(MODELS.keys())
        raise ValueError(
            f"Modelo '{name}' no encontrado en el catálogo.\n"
            f"Disponibles:\n  {available}"
        )
    return model
