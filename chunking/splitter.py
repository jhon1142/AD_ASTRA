"""
Chunking por oraciones completas para AD_ASTRA — CODEFEST 2026.

Características:
- Nunca divide una oración entre dos chunks.
- Mide tokens reales con el tokenizer del encoder.
- Mantiene overlap únicamente mediante oraciones completas.
- Conserva doc_id, fuente, formato, fenómeno y metadata.
- Produce objetos Chunk listos para FAISS.
- CSV/XLSX se mantienen por fila, tal como fueron extraídos.
"""

from __future__ import annotations

import re
from typing import Any

from transformers import AutoTokenizer

from config.settings import (
    CHUNK_SIZE_MAX,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    EMBEDDING_MODEL,
)
from core.chunk import Chunk
from core.document import Document
from embeddings.models import get_embedding_model


class SentenceSplitter:
   

    TABULAR_FORMATS = {
        "csv",
        "xlsx",
        "xls",
    }

    def __init__(
        self,
        target_tokens: int = DEFAULT_CHUNK_SIZE,
        overlap_tokens: int = DEFAULT_CHUNK_OVERLAP,
        max_tokens: int = CHUNK_SIZE_MAX,
        tokenizer_name: str = EMBEDDING_MODEL,
    ) -> None:

        if target_tokens <= 0:
            raise ValueError(
                "target_tokens debe ser mayor que 0"
            )

        if max_tokens < target_tokens:
            raise ValueError(
                "max_tokens debe ser mayor o igual que target_tokens"
            )

        if overlap_tokens < 0:
            raise ValueError(
                "overlap_tokens no puede ser negativo"
            )

        if overlap_tokens >= target_tokens:
            raise ValueError(
                "overlap_tokens debe ser menor que target_tokens"
            )

        self.target_tokens = target_tokens
        self.overlap_tokens = overlap_tokens
        self.max_tokens = max_tokens
        self.tokenizer_name = tokenizer_name

        model_info = get_embedding_model(
            tokenizer_name
        )

        self.encoder_max_tokens = (
            model_info.max_tokens
        )

        if self.max_tokens > self.encoder_max_tokens:
            raise ValueError(
                "El límite de chunk supera la capacidad "
                f"del encoder: {self.max_tokens} > "
                f"{self.encoder_max_tokens}"
            )

        self.tokenizer = AutoTokenizer.from_pretrained(
            tokenizer_name,
            use_fast=True,
        )

        self._nlp = self._create_sentence_segmenter()

    # ------------------------------------------------------------------
    # Tokenización
    # ------------------------------------------------------------------

    def count_tokens(
        self,
        text: str,
    ) -> int:
       

        if not text:
            return 0

        token_ids = self.tokenizer.encode(
            text,
            add_special_tokens=False,
            truncation=False,
        )

        return len(token_ids)

    # ------------------------------------------------------------------
    # Segmentación de oraciones
    # ------------------------------------------------------------------

    @staticmethod
    def _create_sentence_segmenter():
       

        try:
            import spacy

            nlp = spacy.blank("xx")

            if "sentencizer" not in nlp.pipe_names:
                nlp.add_pipe("sentencizer")

            return nlp

        except Exception:
            return None

    @staticmethod
    def _trim_span(
        text: str,
        start: int,
        end: int,
    ) -> tuple[int, int]:
       

        raw = text[start:end]

        left_trim = len(raw) - len(
            raw.lstrip()
        )

        right_trim = len(raw) - len(
            raw.rstrip()
        )

        start += left_trim
        end -= right_trim

        return start, end

    def _sentence_spans(
        self,
        text: str,
    ) -> list[tuple[int, int]]:
       

        if not text or not text.strip():
            return []

        spans: list[tuple[int, int]] = []

        # --------------------------------------------------------------
        # spaCy
        # --------------------------------------------------------------

        if self._nlp is not None:

            doc = self._nlp(text)

            for sentence in doc.sents:

                start, end = self._trim_span(
                    text,
                    sentence.start_char,
                    sentence.end_char,
                )

                if start < end:
                    spans.append(
                        (start, end)
                    )

        # --------------------------------------------------------------
        # Fallback regex
        # --------------------------------------------------------------

        else:

            pattern = re.compile(
                r"[^.!?]+(?:[.!?]+|$)",
                flags=re.MULTILINE,
            )

            for match in pattern.finditer(text):

                start, end = self._trim_span(
                    text,
                    match.start(),
                    match.end(),
                )

                if start < end:
                    spans.append(
                        (start, end)
                    )

        # Si por alguna razón no se detectaron oraciones,
        # conservamos el documento completo.
        if not spans and text.strip():

            start = len(text) - len(
                text.lstrip()
            )

            end = len(
                text.rstrip()
            )

            spans.append(
                (start, end)
            )

        return spans

    # ------------------------------------------------------------------
    # Construcción de chunks
    # ------------------------------------------------------------------

    def _text_from_spans(
        self,
        text: str,
        spans: list[tuple[int, int]],
        start_index: int,
        end_index: int,
    ) -> str:
       

        start_char = spans[start_index][0]
        end_char = spans[end_index - 1][1]

        return text[
            start_char:end_char
        ].strip()

    def _find_overlap_start(
        self,
        text: str,
        spans: list[tuple[int, int]],
        chunk_start: int,
        chunk_end: int,
    ) -> int:
        """
        Busca desde qué oración comenzar el siguiente chunk
        para obtener overlap sin cortar oraciones.
        """

        if self.overlap_tokens == 0:
            return chunk_end

        overlap_start = chunk_end
        accumulated_tokens = 0

        index = chunk_end - 1

        # index > chunk_start evita reutilizar el chunk completo
        # y garantiza avance.
        while index > chunk_start:

            sentence_text = text[
                spans[index][0]:
                spans[index][1]
            ]

            sentence_tokens = self.count_tokens(
                sentence_text
            )

            if (
                accumulated_tokens
                + sentence_tokens
                > self.overlap_tokens
            ):
                break

            accumulated_tokens += (
                sentence_tokens
            )

            overlap_start = index
            index -= 1

        if overlap_start <= chunk_start:
            return chunk_end

        return overlap_start

    def _group_sentence_spans(
        self,
        text: str,
        spans: list[tuple[int, int]],
    ) -> list[str]:
        """
        Agrupa oraciones consecutivas hasta aproximarse.
        """

        chunks: list[str] = []

        start = 0
        total_sentences = len(spans)

        while start < total_sentences:

            end = start
            best_end = start

            while end < total_sentences:

                candidate = self._text_from_spans(
                    text,
                    spans,
                    start,
                    end + 1,
                )

                token_count = self.count_tokens(
                    candidate
                )

                # Chunk dentro del objetivo.
                if token_count <= self.target_tokens:

                    best_end = end + 1
                    end += 1
                    continue

                # Si una única oración supera el objetivo,
                # se conserva completa.
                if best_end == start:

                    if token_count > self.encoder_max_tokens:
                        raise ValueError(
                            "Se encontró una oración que supera "
                            "el límite máximo del encoder "
                            f"({token_count} tokens > "
                            f"{self.encoder_max_tokens}). "
                            "No puede dividirse sin incumplir "
                            "el requisito de oración completa."
                        )

                    best_end = end + 1

                break

            if best_end == start:
                best_end = start + 1

            chunk_text = self._text_from_spans(
                text,
                spans,
                start,
                best_end,
            )

            if chunk_text:
                chunks.append(
                    chunk_text
                )

            if best_end >= total_sentences:
                break

            next_start = self._find_overlap_start(
                text=text,
                spans=spans,
                chunk_start=start,
                chunk_end=best_end,
            )

            # Protección contra loops.
            if next_start <= start:
                next_start = best_end

            start = next_start

        return chunks

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def split_text(
        self,
        text: str,
    ) -> list[str]:
        """
        Divide texto manteniendo oraciones completas.
        """

        spans = self._sentence_spans(
            text
        )

        if not spans:
            return []

        return self._group_sentence_spans(
            text,
            spans,
        )

    def _build_chunk(
        self,
        document: Document,
        text: str,
        position: int,
        total_chunks: int,
        extra_metadata: dict[str, Any] | None = None,
    ) -> Chunk:
        """
        Construye un Chunk preservando todos los campos
        obligatorios del documento original.
        """

        token_count = self.count_tokens(
            text
        )

        if token_count > self.encoder_max_tokens:
            raise ValueError(
                f"Chunk {document.doc_id} posición {position} "
                f"tiene {token_count} tokens y supera "
                f"el máximo del encoder "
                f"({self.encoder_max_tokens})."
            )

        metadata: dict[str, Any] = {
            **document.metadata,
            "total_chunks": total_chunks,
            "splitter": "sentence_token",
            "target_tokens": self.target_tokens,
            "max_tokens": self.max_tokens,
        }

        if extra_metadata:
            metadata.update(
                extra_metadata
            )

        return Chunk(
            chunk_id=(
                f"{document.doc_id}-chunk-"
                f"{position:04d}"
            ),
            doc_id=document.doc_id,
            fuente=document.fuente,
            formato=document.formato,
            fenomeno=document.fenomeno,
            posicion=position,
            num_tokens=token_count,
            texto=text,
            metadata=metadata,
        )

    def split_document(
        self,
        document: Document,
    ) -> list[Chunk]:
        """
        Convierte un Document en uno o varios Chunk.

        CSV/XLSX ya llegan al pipeline como filas independientes,
        por lo que se conserva cada fila como una sola unidad.
        """

        if not document.content.strip():
            return []

        # --------------------------------------------------------------
        # Datos tabulares
        # --------------------------------------------------------------

        if document.formato.lower() in self.TABULAR_FORMATS:

            return [
                self._build_chunk(
                    document=document,
                    text=document.content.strip(),
                    position=0,
                    total_chunks=1,
                    extra_metadata={
                        "structured_row": True,
                    },
                )
            ]

        # --------------------------------------------------------------
        # Texto narrativo
        # --------------------------------------------------------------

        texts = self.split_text(
            document.content
        )

        total_chunks = len(texts)

        return [
            self._build_chunk(
                document=document,
                text=chunk_text,
                position=position,
                total_chunks=total_chunks,
            )
            for position, chunk_text
            in enumerate(texts)
        ]

    def split_documents(
        self,
        documents: list[Document],
    ) -> list[Chunk]:
        """
        Aplica el chunking a todos los documentos.
        """

        chunks: list[Chunk] = []

        for document in documents:

            chunks.extend(
                self.split_document(
                    document
                )
            )

        return chunks