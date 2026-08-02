"""
Utilidades de hashing para AD_ASTRA.

Usadas principalmente para:
- Detectar documentos duplicados antes de indexar.
- Generar doc_id reproducibles a partir del contenido.
- Verificar integridad de archivos.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Union

from core.document import Document


def hash_text(text: str, algorithm: str = "sha256") -> str:
    """
    Genera el hash hexadecimal de una cadena de texto.

    Args:
        text:      Texto a hashear.
        algorithm: Algoritmo de hashlib ('sha256', 'md5', 'sha1', etc.).

    Returns:
        String hexadecimal del hash.
    """
    h = hashlib.new(algorithm)
    h.update(text.encode("utf-8"))
    return h.hexdigest()


def hash_file(path: Union[str, Path], algorithm: str = "sha256", chunk_size: int = 8192) -> str:
    """
    Genera el hash de un archivo leyéndolo en chunks (eficiente para archivos grandes).

    Args:
        path:       Ruta al archivo.
        algorithm:  Algoritmo de hashlib.
        chunk_size: Tamaño de bloque de lectura en bytes.

    Returns:
        String hexadecimal del hash del archivo.
    """
    h = hashlib.new(algorithm)
    with Path(path).open("rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def hash_document(document: Document, algorithm: str = "sha256") -> str:
    """
    Genera un hash del contenido de un Document.

    Args:
        document:  Document a hashear.
        algorithm: Algoritmo de hashlib.

    Returns:
        String hexadecimal del hash del contenido.
    """
    return hash_text(document.content, algorithm=algorithm)


def assign_doc_ids(documents: list[Document], algorithm: str = "sha256") -> list[Document]:
    """
    Asigna un doc_id reproducible a cada Document basado en su contenido.

    Si el documento ya tiene doc_id, no lo modifica.

    Args:
        documents: Lista de Documents.
        algorithm: Algoritmo de hashlib.

    Returns:
        Nueva lista de Documents con doc_id asignado.
    """
    result: list[Document] = []
    for doc in documents:
        if doc.doc_id:
            result.append(doc)
        else:
            result.append(
                Document(
                    content=doc.content,
                    metadata=doc.metadata,
                    doc_id=hash_document(doc, algorithm=algorithm)[:16],
                )
            )
    return result


def deduplicate(documents: list[Document], algorithm: str = "sha256") -> list[Document]:
    """
    Elimina documentos con contenido duplicado conservando el primero encontrado.

    Args:
        documents: Lista de Documents (puede contener duplicados).
        algorithm: Algoritmo para calcular hashes.

    Returns:
        Lista sin duplicados, preservando el orden de aparición.
    """
    seen: set[str] = set()
    unique: list[Document] = []
    for doc in documents:
        h = hash_document(doc, algorithm=algorithm)
        if h not in seen:
            seen.add(h)
            unique.append(doc)
    return unique
