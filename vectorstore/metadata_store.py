"""
Almacén de metadatos asociados a los vectores del índice FAISS.

FAISS almacena únicamente vectores y posiciones enteras.
MetadataStore mantiene la correspondencia exacta entre:

    FAISS internal ID <-> metadata.jsonl <-> Chunk

El orden de los registros es crítico:
la línea N de metadata.jsonl corresponde al vector N del índice FAISS.
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any

from config.settings import VECTORSTORE_PATH
from core.chunk import Chunk
from core.document import Document


class MetadataStore:
  

    def __init__(
        self,
        store_documents: bool = True,
    ) -> None:
        self.store_documents = store_documents
        self._records: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Gestión de registros
    # ------------------------------------------------------------------

    def add(
        self,
        chunks: list[Chunk],
    ) -> None:
       

        for chunk in chunks:

            faiss_id = len(self._records)

            record = chunk.to_metadata_record()

            # Guardamos explícitamente el ID interno para facilitar
            # auditoría y trazabilidad.
            record["faiss_id"] = faiss_id

            self._records.append(record)

    def get(
        self,
        index: int,
    ) -> dict[str, Any]:
       

        if index < 0 or index >= len(self._records):
            raise IndexError(
                f"Índice {index} fuera de rango "
                f"(total: {len(self._records)})"
            )

        return self._records[index]

    # ------------------------------------------------------------------
    # Recuperación como Chunk
    # ------------------------------------------------------------------

    def get_chunk(
        self,
        index: int,
    ) -> Chunk:
       

        record = self.get(index)

        return Chunk.from_metadata_record(record)

    def get_chunks(
        self,
        indices: list[int],
    ) -> list[Chunk]:
        

        chunks: list[Chunk] = []

        for index in indices:

            if index == -1:
                continue

            chunks.append(
                self.get_chunk(index)
            )

        return chunks

    # ------------------------------------------------------------------
    # Recuperación compatible como Document
    # ------------------------------------------------------------------

    def get_documents(
        self,
        indices: list[int],
    ) -> list[Document]:
       

        documents: list[Document] = []

        chunks = self.get_chunks(indices)

        for chunk in chunks:

            metadata: dict[str, Any] = {
                # Campos obligatorios del chunk
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "fuente": chunk.fuente,
                "formato": chunk.formato,
                "fenomeno": chunk.fenomeno,
                "posicion": chunk.posicion,
                "num_tokens": chunk.num_tokens,
                "texto": chunk.texto,

                # ID interno de FAISS
                "faiss_id": chunk.faiss_id,
            }

            # Metadata adicional:
            # idioma, página, título, sección, URL, etc.
            metadata.update(chunk.metadata)

            

            metadata.setdefault(
                "source",
                chunk.fuente,
            )

            metadata.setdefault(
                "file_type",
                chunk.formato,
            )

            if "idioma" in metadata:
                metadata.setdefault(
                    "language",
                    metadata["idioma"],
                )

            documents.append(
                Document(
                    doc_id=chunk.doc_id,
                    fuente=chunk.fuente,
                    formato=chunk.formato,
                    fenomeno=chunk.fenomeno,
                    content=chunk.texto,
                    metadata=metadata,
                )
            )

        return documents

    # ------------------------------------------------------------------
    # Información del store
    # ------------------------------------------------------------------

    @property
    def size(self) -> int:
        """Número total de registros almacenados."""

        return len(self._records)

    def __len__(self) -> int:
        """Permite utilizar len(metadata_store)."""

        return self.size

    # ------------------------------------------------------------------
    # Validación
    # ------------------------------------------------------------------

    def validate_required_fields(self) -> None:
        """
        Verifica que todos los registros tengan los campos obligatorios.

        Raises:
            ValueError:
                Si algún registro está incompleto.
        """

        required_fields = {
            "chunk_id",
            "doc_id",
            "fuente",
            "formato",
            "fenomeno",
            "posicion",
            "num_tokens",
            "texto",
        }

        for index, record in enumerate(self._records):

            missing = required_fields - record.keys()

            if missing:
                raise ValueError(
                    f"Registro FAISS {index} incompleto. "
                    f"Faltan campos: {sorted(missing)}"
                )

    def validate_faiss_alignment(self) -> None:
        """
        Verifica que faiss_id coincida con el número de línea/posición.

        Esto garantiza:

            FAISS ID N == metadata.jsonl línea N
        """

        for expected_id, record in enumerate(self._records):

            faiss_id = record.get(
                "faiss_id",
                expected_id,
            )

            if int(faiss_id) != expected_id:
                raise ValueError(
                    "Desalineación FAISS/metadata detectada: "
                    f"posición={expected_id}, "
                    f"faiss_id={faiss_id}"
                )

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------

    def save(
        self,
        path: Path | str | None = None,
        format: str = "json",
    ) -> Path:
        """
        Guarda el MetadataStore.

        Para CODEFEST el formato principal es JSONL:
        exactamente un objeto JSON por línea.

        Args:
            path:
                Ruta de destino.
            format:
                ``json`` o ``pickle``.

        Returns:
            Ruta del archivo generado.
        """

        if format not in (
            "json",
            "pickle",
        ):
            raise ValueError(
                "format debe ser 'json' o 'pickle'"
            )

        # Validamos antes de persistir.
        self.validate_required_fields()
        self.validate_faiss_alignment()

        extension = (
            "jsonl"
            if format == "json"
            else "pkl"
        )

        save_path = (
            Path(path)
            if path
            else Path(VECTORSTORE_PATH)
            / f"metadata.{extension}"
        )

        save_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if format == "json":

            with save_path.open(
                "w",
                encoding="utf-8",
            ) as file:

                for record in self._records:

                    file.write(
                        json.dumps(
                            record,
                            ensure_ascii=False,
                        )
                    )

                    file.write("\n")

        else:

            with save_path.open(
                "wb"
            ) as file:

                pickle.dump(
                    self._records,
                    file,
                )

        return save_path

    # ------------------------------------------------------------------
    # Carga desde disco
    # ------------------------------------------------------------------

    @classmethod
    def load(
        cls,
        path: Path | str,
        store_documents: bool = True,
    ) -> "MetadataStore":
        """
        Carga metadata desde JSON, JSONL o pickle.

        Args:
            path:
                Ruta al archivo.
            store_documents:
                Mantiene compatibilidad con la interfaz existente.

        Returns:
            MetadataStore reconstruido.
        """

        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(
                f"No existe el archivo de metadata: {path}"
            )

        instance = cls(
            store_documents=store_documents
        )

        # --------------------------------------------------------------
        # JSON tradicional
        # --------------------------------------------------------------

        if path.suffix.lower() == ".json":

            data = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

            if not isinstance(data, list):
                raise ValueError(
                    "El archivo JSON debe contener una lista "
                    "de registros."
                )

            instance._records = data

        # --------------------------------------------------------------
        # JSON Lines
        # --------------------------------------------------------------

        elif path.suffix.lower() == ".jsonl":

            records: list[dict[str, Any]] = []

            with path.open(
                "r",
                encoding="utf-8",
            ) as file:

                for line_number, line in enumerate(
                    file,
                    start=1,
                ):

                    line = line.strip()

                    if not line:
                        continue

                    try:
                        record = json.loads(line)

                    except json.JSONDecodeError as exc:
                        raise ValueError(
                            "JSON inválido en metadata.jsonl "
                            f"línea {line_number}"
                        ) from exc

                    if not isinstance(record, dict):
                        raise ValueError(
                            "Cada línea de metadata.jsonl "
                            "debe ser un objeto JSON. "
                            f"Error en línea {line_number}."
                        )

                    records.append(record)

            instance._records = records

        # --------------------------------------------------------------
        # Pickle
        # --------------------------------------------------------------

        elif path.suffix.lower() in (
            ".pkl",
            ".pickle",
        ):

            with path.open(
                "rb"
            ) as file:

                instance._records = pickle.load(
                    file
                )

        else:

            raise ValueError(
                "Formato de metadata no soportado: "
                f"{path.suffix}"
            )

        # --------------------------------------------------------------
        # Validaciones después de cargar
        # --------------------------------------------------------------

        instance.validate_required_fields()
        instance.validate_faiss_alignment()

        return instance