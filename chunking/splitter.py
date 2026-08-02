"""
Splitter recursivo por caracteres para documentos AD_ASTRA.

Estrategia: divide por separadores en orden de prioridad hasta que
cada chunk esté dentro del tamaño máximo.
"""
from __future__ import annotations

from config.settings import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP
from core.document import Document


class RecursiveCharacterSplitter:
    """
    Divide texto recursivamente usando una lista de separadores priorizados.

    El algoritmo intenta dividir por el primer separador de la lista;
    si algún fragmento sigue siendo demasiado grande, lo vuelve a dividir
    con el siguiente separador.

    Args:
        chunk_size:    Tamaño máximo de cada chunk en caracteres.
        chunk_overlap: Número de caracteres solapados entre chunks consecutivos.
        separators:    Lista de separadores en orden de prioridad.
                       Por defecto: párrafo → línea → oración → espacio → carácter.
        keep_separator: Si True, el separador queda al final del chunk.
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""]

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        separators: list[str] | None = None,
        keep_separator: bool = True,
    ) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap debe ser menor que chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or self.DEFAULT_SEPARATORS
        self.keep_separator = keep_separator

    # ------------------------------------------------------------------
    # Lógica interna
    # ------------------------------------------------------------------

    def _merge_splits(self, splits: list[str], separator: str) -> list[str]:
        """Une splits pequeños respetando chunk_size y chunk_overlap."""
        chunks: list[str] = []
        current: list[str] = []
        current_len = 0

        for split in splits:
            split_len = len(split)
            if current_len + split_len > self.chunk_size and current:
                chunk = separator.join(current).strip()
                if chunk:
                    chunks.append(chunk)
                # Retroceder overlap
                while current and current_len > self.chunk_overlap:
                    current_len -= len(current[0]) + len(separator)
                    current.pop(0)
            current.append(split)
            current_len += split_len + len(separator)

        if current:
            chunk = separator.join(current).strip()
            if chunk:
                chunks.append(chunk)

        return chunks

    def _split_text(self, text: str, separators: list[str]) -> list[str]:
        """División recursiva."""
        separator = separators[0]
        next_separators = separators[1:]

        splits = text.split(separator) if separator else list(text)

        good: list[str] = []
        bad: list[str] = []

        for s in splits:
            if len(s) <= self.chunk_size:
                good.append(s)
            elif next_separators:
                bad.extend(self._split_text(s, next_separators))
            else:
                bad.append(s)

        all_splits = good + bad
        return self._merge_splits(all_splits, separator)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def split_text(self, text: str) -> list[str]:
        """Divide una cadena y devuelve lista de chunks."""
        return self._split_text(text, self.separators)

    def split_document(self, document: Document) -> list[Document]:
        """
        Divide un Document y devuelve una lista de Documents hijos.
        Los metadatos del documento original se heredan.
        """
        chunks = self.split_text(document.content)
        return [
            Document(
                content=chunk,
                metadata={
                    **document.metadata,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                },
                doc_id=f"{document.doc_id}_chunk{i}" if document.doc_id else "",
            )
            for i, chunk in enumerate(chunks)
        ]

    def split_documents(self, documents: list[Document]) -> list[Document]:
        """Aplica split_document() a una lista de documentos."""
        result: list[Document] = []
        for doc in documents:
            result.extend(self.split_document(doc))
        return result
