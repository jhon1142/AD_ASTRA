"""
Almacén de metadatos asociados a los vectores del índice FAISS.

FAISS solo almacena vectores numéricos con índices enteros.
MetadataStore mantiene el mapeo índice_faiss → Document / metadatos.
"""
from __future__ import annotations

import json
import pickle
from pathlib import Path
from core.chunk import Chunk

from config.settings import VECTORSTORE_PATH
from core.document import Document


class MetadataStore:
    """
    Almacén clave-valor que asocia cada posición del índice FAISS
    con el Document y sus metadatos originales.

    Internamente usa una lista ordenada: la posición i corresponde
    al vector i en FAISSManager.

    Args:
        store_documents: Si True, guarda el contenido completo del Document.
                         Si False, solo guarda los metadatos (ahorra memoria).
    """

    def __init__(self, store_documents: bool = True) -> None:
        self.store_documents = store_documents
        self._records: list[dict] = []

    # ------------------------------------------------------------------
    # Gestión de registros
    # ------------------------------------------------------------------

    def add(self, chunks: list[Chunk]) -> None:
        """
        Agrega chunks al store en el mismo orden en que sus vectores
    fueron agregados a FAISSManager.

    Args:
        chunks: Lista de Chunk cuyas posiciones coinciden con
                los vectores recién agregados al índice.
        """
        for chunk in chunks:
            self._records.append(
                chunk.to_metadata_record()
            )

    def get(self, index: int) -> dict:
        """
        Devuelve el registro asociado a la posición `index` del índice FAISS.

        Args:
            index: Posición entera en el índice FAISS.

        Returns:
            Diccionario con 'content' (opcional), 'metadata' y 'doc_id'.

        Raises:
            IndexError: Si el índice está fuera de rango.
        """
        if index < 0 or index >= len(self._records):
            raise IndexError(f"Índice {index} fuera de rango (total: {len(self._records)})")
        return self._records[index]

    def get_documents(self, indices: list[int]) -> list[Document]:
        """
        Recupera Documents a partir de una lista de índices FAISS.

        Args:
            indices: Lista de posiciones enteras (e.g., retornadas por FAISSManager.search).

        Returns:
            Lista de Documents. Los índices inválidos (-1) se omiten.
        """
        documents: list[Document] = []
        for idx in indices:
            if idx == -1:  # FAISS usa -1 para resultados vacíos
                continue
            record = self.get(idx)
            documents.append(
                Document(
                    doc_id=record["doc_id"],
                    fuente=record["fuente"],
                    formato=record["formato"],
                    fenomeno=record["fenomeno"],
                    content=record["texto"],
                    metadata={},
                )
            )
        return documents

    @property
    def size(self) -> int:
        """Número de registros almacenados."""
        return len(self._records)

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------

    def save(self, path: Path | str | None = None, format: str = "json") -> Path:
        """
        Guarda el store en disco.

        Args:
            path:   Ruta del archivo. Por defecto usa VECTORSTORE_PATH/metadata.json.
            format: 'json' o 'pickle'. JSON es legible; pickle soporta cualquier tipo.

        Returns:
            Ruta donde se guardó el store.
        """
        if format not in ("json", "pickle"):
            raise ValueError("format debe ser 'json' o 'pickle'")

        ext = "jsonl" if format == "json" else "pkl"
        save_path = Path(path) if path else Path(VECTORSTORE_PATH) / f"metadata.{ext}"
        save_path.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            with save_path.open("w", encoding="utf-8") as f:
                for record in self._records:
                    f.write(
                        json.dumps(record, ensure_ascii=False)
                    )
                    f.write("\n")
        else:
            with save_path.open("wb") as f:
                pickle.dump(self._records, f)

        return save_path

    @classmethod
    def load(
        cls,
        path: Path | str,
        store_documents: bool = True
    ) -> "MetadataStore":
        """
        Carga el store desde disco.

        Args:
            path:            Ruta al archivo (.json o .pkl).
            store_documents: Parámetro de la instancia creada.

        Returns:
            Instancia de MetadataStore con los registros cargados.
        """
        path = Path(path)
        instance = cls(store_documents=store_documents)

        if path.suffix == ".json":
            instance._records = json.loads(
                path.read_text(encoding="utf-8")
            )

        elif path.suffix == ".jsonl":
            with path.open("r", encoding="utf-8") as f:
                instance._records = [
                    json.loads(line)
                    for line in f
                    if line.strip()
                ]

        elif path.suffix in (".pkl", ".pickle"):
            with path.open("rb") as f:
                instance._records = pickle.load(f)

        else:
            raise ValueError(
                f"Formato de archivo no soportado: {path.suffix}"
            )

        return instance
    