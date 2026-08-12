"""
Pipeline de construcción del índice vectorial para AD_ASTRA.

Flujo:
    load -> clean -> sentence chunking -> embeddings
    -> FAISS -> metadata.jsonl
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Union

import torch

from chunking.sentence_splitter import SentenceSplitter
from config.settings import (
    CHUNK_SIZE_MAX,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_MODEL,
    VECTORSTORE_PATH,
)
from core.chunk import Chunk
from embeddings.encoder import Encoder
from pipeline.load_documents import load_and_clean
from preprocessing.cleaner import TextCleaner
from vectorstore.faiss_manager import FAISSManager
from vectorstore.metadata_store import MetadataStore


def _detect_device() -> str:
   

    if torch.cuda.is_available():
        return "cuda"

    if (
        hasattr(torch.backends, "mps")
        and torch.backends.mps.is_available()
    ):
        return "mps"

    return "cpu"


def build_index(
    sources: list[Union[str, Path]],

    # Chunking
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    chunk_max_tokens: int = CHUNK_SIZE_MAX,

    # Embeddings
    embedding_model: str = EMBEDDING_MODEL,
    batch_size: int = EMBEDDING_BATCH_SIZE,

    # Vectorstore
    index_type: str = "flat_ip",
    save_path: Path | str | None = None,

    # Opciones
    cleaner: TextCleaner | None = None,
    verbose: bool = True,

) -> tuple[FAISSManager, MetadataStore]:
    

    start_time = time.perf_counter()

    # ------------------------------------------------------------------
    # 1. Carga y limpieza
    # ------------------------------------------------------------------

    _log(
        verbose,
        f"[1/4] Cargando {len(sources)} fuente(s)..."
    )

    documents = load_and_clean(
        sources,
        cleaner=cleaner,
    )

    _log(
        verbose,
        f"      {len(documents)} documento(s) "
        "cargados y limpios."
    )

    if not documents:
        raise ValueError(
            "No se cargó ningún documento."
        )

    # ------------------------------------------------------------------
    # 2. Chunking por oraciones completas
    # ------------------------------------------------------------------

    _log(
        verbose,
        (
            "[2/4] Chunking por oraciones "
            f"(target={chunk_size} tokens, "
            f"max={chunk_max_tokens}, "
            f"overlap={chunk_overlap})..."
        ),
    )

    splitter = SentenceSplitter(
        target_tokens=chunk_size,
        overlap_tokens=chunk_overlap,
        max_tokens=chunk_max_tokens,
        tokenizer_name=embedding_model,
    )

    chunks: list[Chunk] = (
        splitter.split_documents(
            documents
        )
    )

    if not chunks:
        raise ValueError(
            "El chunker no generó ningún fragmento."
        )

    _log(
        verbose,
        f"      {len(chunks)} chunk(s) generados."
    )

    token_counts = [
        chunk.num_tokens
        for chunk in chunks
    ]

    _log(
        verbose,
        (
            "      Tokens/chunk: "
            f"min={min(token_counts)}, "
            f"promedio="
            f"{sum(token_counts) / len(token_counts):.1f}, "
            f"max={max(token_counts)}"
        ),
    )

    # ------------------------------------------------------------------
    # 3. Embeddings
    # ------------------------------------------------------------------

    device = _detect_device()

    _log(
        verbose,
        (
            f"[3/4] Embeddings con "
            f"'{embedding_model}' "
            f"en dispositivo '{device}'..."
        ),
    )

    encoder = Encoder(
        model_name=embedding_model,
        batch_size=batch_size,
        device=device,
        show_progress=verbose,
    )

    vectors = encoder.encode_chunks(
        chunks
    )

    if len(vectors) != len(chunks):
        raise RuntimeError(
            "La cantidad de embeddings no coincide "
            "con la cantidad de chunks."
        )

    _log(
        verbose,
        f"      Vectores shape: {vectors.shape}"
    )

    # ------------------------------------------------------------------
    # 4. FAISS + Metadata
    # ------------------------------------------------------------------

    _log(
        verbose,
        "[4/4] Indexando en FAISS..."
    )

    faiss_manager = FAISSManager(
        dimensions=encoder.dimensions,
        index_type=index_type,
    )

    if index_type == "ivf_flat":

        faiss_manager.train(
            vectors
        )

    faiss_manager.add(
        vectors
    )

    metadata_store = MetadataStore(
        store_documents=True
    )

    metadata_store.add(
        chunks
    )

    # Debe cumplirse:
    # 1 vector FAISS <-> 1 línea metadata.
    if faiss_manager.size != metadata_store.size:
        raise RuntimeError(
            "FAISS y MetadataStore quedaron desalineados: "
            f"{faiss_manager.size} vectores vs "
            f"{metadata_store.size} registros."
        )

    metadata_store.validate_required_fields()
    metadata_store.validate_faiss_alignment()

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------

    base = (
        Path(save_path)
        if save_path
        else Path(VECTORSTORE_PATH)
    )

    base.mkdir(
        parents=True,
        exist_ok=True,
    )

    index_file = faiss_manager.save(
        base / "index.faiss"
    )

    metadata_file = metadata_store.save(
        base / "metadata.jsonl"
    )

    elapsed = (
        time.perf_counter()
        - start_time
    )

    _log(
        verbose,
        f"\n✓ Índice construido en {elapsed:.1f}s"
    )

    _log(
        verbose,
        f"  FAISS → {index_file}"
    )

    _log(
        verbose,
        f"  Meta  → {metadata_file}"
    )

    _log(
        verbose,
        f"  Total vectores: {faiss_manager.size}"
    )

    return (
        faiss_manager,
        metadata_store,
    )


def _log(
    verbose: bool,
    message: str,
) -> None:

    if verbose:
        print(message)


if __name__ == "__main__":

    sources = [
        path
        for path in Path("data/raw").rglob("*")
        if path.is_file()
    ]

    print(
        f"Fuentes encontradas: {len(sources)}"
    )

    build_index(
        sources=sources
    )