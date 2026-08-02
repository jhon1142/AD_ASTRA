"""
Splitter basado en oraciones para documentos AD_ASTRA.

Usa spaCy para segmentación precisa de oraciones cuando está disponible,
con fallback a regex para entornos sin spaCy.
"""
from __future__ import annotations

import re

from config.settings import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP
from core.document import Document


class SentenceSplitter:
    """
    Divide texto en chunks respetando límites de oración.

    Agrupa oraciones consecutivas hasta alcanzar chunk_size caracteres,
    luego inicia un nuevo chunk con solapamiento opcional.

    Args:
        chunk_size:    Tamaño máximo de cada chunk en caracteres.
        chunk_overlap: Número de oraciones solapadas entre chunks consecutivos.
        spacy_model:   Modelo de spaCy a usar, e.g. 'es_core_news_sm'.
                       Si es None o no está instalado, usa regex.
    """

    # Regex de fallback: divide en puntos, signos de exclamación e interrogación
    _SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        spacy_model: str | None = None,
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.spacy_model = spacy_model
        self._nlp = self._load_spacy(spacy_model)

    @staticmethod
    def _load_spacy(model: str | None):
        if model is None:
            return None
        try:
            import spacy
            return spacy.load(model, disable=["ner", "tagger", "parser", "lemmatizer"])
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Segmentación
    # ------------------------------------------------------------------

    def _get_sentences(self, text: str) -> list[str]:
        """Devuelve lista de oraciones usando spaCy o regex."""
        if self._nlp is not None:
            doc = self._nlp(text)
            return [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        return [s.strip() for s in self._SENTENCE_RE.split(text) if s.strip()]

    # ------------------------------------------------------------------
    # Agrupación en chunks
    # ------------------------------------------------------------------

    def _group_sentences(self, sentences: list[str]) -> list[str]:
        """Agrupa oraciones en chunks respetando chunk_size y chunk_overlap."""
        chunks: list[str] = []
        start = 0

        while start < len(sentences):
            current_chunk: list[str] = []
            current_len = 0
            i = start

            while i < len(sentences):
                sent = sentences[i]
                if current_len + len(sent) + 1 > self.chunk_size and current_chunk:
                    break
                current_chunk.append(sent)
                current_len += len(sent) + 1
                i += 1

            chunks.append(" ".join(current_chunk))

            # Avanzar dejando overlap de oraciones
            overlap_chars = 0
            overlap_start = i - 1
            while overlap_start > start and overlap_chars < self.chunk_overlap:
                overlap_chars += len(sentences[overlap_start])
                overlap_start -= 1

            start = max(start + 1, overlap_start + 1)

        return chunks

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def split_text(self, text: str) -> list[str]:
        """Divide una cadena respetando límites de oración."""
        sentences = self._get_sentences(text)
        if not sentences:
            return [text] if text.strip() else []
        return self._group_sentences(sentences)

    def split_document(self, document: Document) -> list[Document]:
        """Divide un Document en chunks a nivel de oración."""
        chunks = self.split_text(document.content)
        return [
            Document(
                content=chunk,
                metadata={
                    **document.metadata,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "splitter": "sentence",
                },
                doc_id=f"{document.doc_id}_sent{i}" if document.doc_id else "",
            )
            for i, chunk in enumerate(chunks)
        ]

    def split_documents(self, documents: list[Document]) -> list[Document]:
        """Aplica split_document() a una lista de documentos."""
        result: list[Document] = []
        for doc in documents:
            result.extend(self.split_document(doc))
        return result
