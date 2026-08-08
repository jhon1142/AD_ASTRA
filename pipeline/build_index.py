"""
Pipeline de construcción del índice vectorial para AD_ASTRA.

Orquesta: load → clean → chunk → embed → store (FAISS + MetadataStore).
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Union

from config.settings import (
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CHUNK_OVERLAP,
    EMBEDDING_MODEL,
    EMBEDDING_BATCH_SIZE,
    VECTORSTORE_PATH,
)
from chunking.splitter import RecursiveCharacterSplitter
from core.chunk import Chunk
from embeddings.encoder import Encoder
from pipeline.load_documents import load_and_clean
from preprocessing.cleaner import TextCleaner
from vectorstore.faiss_manager import FAISSManager
from vectorstore.metadata_store import MetadataStore


def build_index(
    sources: list[Union[str, Path]],
    # ── Chunking ─────────────────────────────────────────────
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    # ── Embeddings ───────────────────────────────────────────
    embedding_model: str = EMBEDDING_MODEL,
    batch_size: int = EMBEDDING_BATCH_SIZE,
    api_key: str | None = None,
    # ── Vectorstore ──────────────────────────────────────────
    index_type: str = "flat_ip",
    save_path: Path | str | None = None,
    # ── Opciones ─────────────────────────────────────────────
    cleaner: TextCleaner | None = None,
    verbose: bool = True,
) -> tuple[FAISSManager, MetadataStore]:
    """
    Construye el índice vectorial completo desde las fuentes indicadas.

    Pasos:
        1. Carga y limpieza de documentos.
        2. Chunking recursivo por caracteres.
        3. Generación de embeddings.
        4. Indexación en FAISS + MetadataStore.
        5. Persistencia en disco.

    Args:
        sources:         Lista de rutas o URLs a indexar.
        chunk_size:      Tamaño máximo de chunk en caracteres.
        chunk_overlap:   Solapamiento entre chunks.
        embedding_model: Nombre del modelo de embedding (ver embeddings/models.py).
        batch_size:      Tamaño de batch para la API de embeddings.
        api_key:         API key del proveedor (None = variable de entorno).
        index_type:      Tipo de índice FAISS ('flat_l2', 'flat_ip', 'ivf_flat').
        save_path:       Directorio donde guardar el índice. None = VECTORSTORE_PATH.
        cleaner:         TextCleaner personalizado. None = configuración por defecto.
        verbose:         Imprimir progreso en consola.

    Returns:
        Tupla (FAISSManager, MetadataStore) ya persistidos en disco.
    """
    t_start = time.perf_counter()

    # ── 1. Carga y limpieza ──────────────────────────────────────────────
    _log(verbose, f"[1/4] Cargando {len(sources)} fuente(s)...")
    documents = load_and_clean(sources, cleaner=cleaner)
    _log(verbose, f"      {len(documents)} documento(s) cargados y limpios.")

    # ── 2. Chunking ──────────────────────────────────────────────────────
    _log(verbose, f"[2/4] Chunking (size={chunk_size}, overlap={chunk_overlap})...")
    splitter = RecursiveCharacterSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    chunks: list[Chunk] = splitter.split_documents(documents)
    _log(verbose, f"      {len(chunks)} chunk(s) generados.")

    # ── 3. Embeddings ────────────────────────────────────────────────────
    _log(verbose, f"[3/4] Generando embeddings con '{embedding_model}'...")
    encoder = Encoder(model_name=embedding_model, batch_size=batch_size, api_key=api_key)
    vectors = encoder.encode_chunks(chunks)
    _log(verbose, f"      Vectores shape: {vectors.shape}")

    # ── 4. Indexación ────────────────────────────────────────────────────
    _log(verbose, "[4/4] Indexando en FAISS y guardando...")
    faiss_mgr = FAISSManager(dimensions=encoder.dimensions, index_type=index_type)

    if index_type == "ivf_flat":
        faiss_mgr.train(vectors)

    faiss_mgr.add(vectors)

    meta_store = MetadataStore(store_documents=True)
    meta_store.add(chunks)

    # ── Persistencia ────────────────────────────────────────────────────
    base = Path(save_path) if save_path else Path(VECTORSTORE_PATH)
    base.mkdir(parents=True, exist_ok=True)

    index_file = faiss_mgr.save(base / "index.faiss")
    meta_file = meta_store.save(base / "metadata.jsonl")

    elapsed = time.perf_counter() - t_start
    _log(verbose, f"\n✓ Índice construido en {elapsed:.1f}s")
    _log(verbose, f"  FAISS  → {index_file}")
    _log(verbose, f"  Meta   → {meta_file}")
    _log(verbose, f"  Total vectores: {faiss_mgr.size}")

    return faiss_mgr, meta_store


def _log(verbose: bool, msg: str) -> None:
    if verbose:
        print(msg)
