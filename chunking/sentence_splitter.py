"""
Chunking por oraciones completas para AD_ASTRA — CODEFEST 2026.

Características:
- Nunca divide una oración entre dos chunks.
- Mide tokens reales con el tokenizer del encoder.
- Mantiene overlap únicamente mediante oraciones completas.
- Conserva doc_id, fuente, formato, fenómeno y metadata.
- Produce objetos Chunk listos para FAISS.
- CSV/XLSX se mantienen por fila.
- Todas las filas de un mismo archivo tabular pueden compartir doc_id.
- Cada fila tabular recibe posicion y chunk_id únicos.
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
    """
    Divide documentos respetando límites completos de oración.

    Para documentos narrativos:
    - agrupa oraciones completas;
    - utiliza tokens reales;
    - aplica overlap mediante oraciones completas.

    Para CSV/XLSX:
    - cada fila permanece como fragmento independiente;
    - todas las filas del archivo pueden compartir doc_id;
    - cada fila recibe posicion y chunk_id únicos.
    """

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
            use_fast=False,
        )

        self._nlp = self._create_sentence_segmenter()

    # ------------------------------------------------------------------
    # Tokenización
    # ------------------------------------------------------------------

    def count_tokens(
        self,
        text: str,
    ) -> int:
        """
        Cuenta tokens reales utilizando el tokenizer
        correspondiente al encoder configurado.
        """

        if not isinstance(text, str):
            print(
                f"[ERROR TOKENIZER] "
                f"type={type(text)} "
                f"value={repr(text)[:300]}"
            )
            raise TypeError(
                f"count_tokens recibió {type(text)}"
            )

        if not text:
            return 0

        try:
            return len(
                self.tokenizer(
                    str(text),
                    add_special_tokens=False,
                    truncation=False,
                )["input_ids"]
            )

        except Exception as e:
            print("\n=== TOKENIZER ERROR ===")
            print("TYPE:", type(text))
            print("VALUE:", repr(text[:500]))
            print("ERROR:", e)
            print("=======================\n")
            raise

    # ------------------------------------------------------------------
    # Segmentación de oraciones
    # ------------------------------------------------------------------

    @staticmethod
    def _create_sentence_segmenter():
        """
        Crea un segmentador multilingüe ligero con spaCy.

        Si spaCy no está disponible, posteriormente se utiliza regex.
        """

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
        """
        Elimina espacios únicamente de los extremos del span,
        conservando intacto el contenido interno.
        """

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
        """
        Obtiene posiciones de inicio y fin de cada oración.

        Utilizar offsets permite recuperar posteriormente el texto
        directamente del contenido original limpio.
        """

        if not text or not text.strip():
            return []

        spans: list[tuple[int, int]] = []

        # --------------------------------------------------------------
        # Segmentación con spaCy
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
        # Fallback mediante regex
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

        # Si no fue posible detectar oraciones,
        # conserva el texto completo como una unidad.
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
    # Construcción de texto desde spans
    # ------------------------------------------------------------------

    def _text_from_spans(
        self,
        text: str,
        spans: list[tuple[int, int]],
        start_index: int,
        end_index: int,
    ) -> str:
        """
        Extrae un fragmento directamente del texto original.

        end_index es exclusivo.
        """

        start_char = spans[start_index][0]
        end_char = spans[end_index - 1][1]

        result = text[
            start_char:end_char
        ]

        if result is None:
            return ""

        return str(result).strip()

    # ------------------------------------------------------------------
    # Overlap
    # ------------------------------------------------------------------

    def _find_overlap_start(
        self,
        text: str,
        spans: list[tuple[int, int]],
        chunk_start: int,
        chunk_end: int,
    ) -> int:
        """
        Calcula desde qué oración debe comenzar el siguiente chunk.

        El overlap se realiza exclusivamente mediante oraciones completas.
        """

        if self.overlap_tokens == 0:
            return chunk_end

        overlap_start = chunk_end
        accumulated_tokens = 0

        index = chunk_end - 1

        # index > chunk_start impide reutilizar el chunk entero
        # y garantiza que siempre exista avance.
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

    # ------------------------------------------------------------------
    # Agrupación de oraciones
    # ------------------------------------------------------------------

    def _group_sentence_spans(
        self,
        text: str,
        spans: list[tuple[int, int]],
    ) -> list[str]:
        """
        Agrupa oraciones consecutivas respetando target_tokens.

        Nunca corta una oración por la mitad.
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

                if not isinstance(candidate, str):
                    print(
                        f"[CANDIDATE TYPE ERROR] "
                        f"{type(candidate)}"
                    )
                token_count = self.count_tokens(
                    candidate
                )

                # La oración o conjunto de oraciones todavía
                # está dentro del tamaño objetivo.
                if token_count <= self.target_tokens:

                    best_end = end + 1
                    end += 1

                    continue

                # Si una sola oración supera target_tokens,
                # debe conservarse completa.
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

            # Protección contra loops infinitos.
            if next_start <= start:
                next_start = best_end

            start = next_start

        return chunks

    # ------------------------------------------------------------------
    # API pública de texto
    # ------------------------------------------------------------------

    def split_text(
        self,
        text: str,
    ) -> list[str]:
        """
        Divide texto narrativo manteniendo oraciones completas.
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

    # ------------------------------------------------------------------
    # Construcción del objeto Chunk
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # División de un documento individual
    # ------------------------------------------------------------------

    def split_document(
        self,
        document: Document,
    ) -> list[Chunk]:
        """
        Convierte un Document en uno o varios Chunk.

        Para documentos narrativos:
            genera múltiples chunks por oraciones.

        Para una fila CSV/XLSX individual:
            utiliza fila_indice como posición provisional.

        El procesamiento completo de datos tabulares se realiza
        principalmente mediante split_documents().
        """
        if document.content is None:
            return []
            
        if not isinstance(document.content, str):
            document.content = str(document.content)

        if not document.content.strip():
            return []

        # --------------------------------------------------------------
        # Datos tabulares
        # --------------------------------------------------------------

        if (
            document.formato.lower()
            in self.TABULAR_FORMATS
        ):

            position = int(
                document.metadata.get(
                    "fila_indice",
                    0,
                )
            )

            return [
                self._build_chunk(
                    document=document,
                    text=document.content.strip(),
                    position=position,
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

        total_chunks = len(
            texts
        )

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

    # ------------------------------------------------------------------
    # División de múltiples documentos
    # ------------------------------------------------------------------

    def split_documents(
        self,
        documents: list[Document],
    ) -> list[Chunk]:
        """
        Aplica chunking a todos los documentos.

        Para CSV/XLSX:
        - todas las filas del archivo comparten doc_id;
        - cada fila recibe una posición consecutiva;
        - cada fila recibe chunk_id único;
        - total_chunks representa la cantidad total de filas útiles.

        Para documentos narrativos:
        utiliza split_document().
        """

        chunks: list[Chunk] = []

        # --------------------------------------------------------------
        # Primera pasada
        #
        # Contar cuántas filas útiles existen para cada documento
        # tabular identificado por doc_id.
        # --------------------------------------------------------------

        tabular_totals: dict[str, int] = {}

        for document in documents:

            if document.content is None:
                continue

            if not isinstance(document.content, str):
                document.content = str(document.content)

            if not document.content.strip():
                continue

            if (
                document.formato.lower()
                in self.TABULAR_FORMATS
            ):

                tabular_totals[
                    document.doc_id
                ] = (
                    tabular_totals.get(
                        document.doc_id,
                        0,
                    )
                    + 1
                )

        # --------------------------------------------------------------
        # Segunda pasada
        #
        # Asignar posiciones consecutivas dentro de cada archivo.
        # --------------------------------------------------------------

        tabular_positions: dict[str, int] = {}

        for document in documents:

            if not document.content.strip():
                continue

            # ----------------------------------------------------------
            # CSV / XLSX
            # ----------------------------------------------------------

            if (
                document.formato.lower()
                in self.TABULAR_FORMATS
            ):

                position = (
                    tabular_positions.get(
                        document.doc_id,
                        0,
                    )
                )

                total_chunks = (
                    tabular_totals[
                        document.doc_id
                    ]
                )

                chunks.append(
                    self._build_chunk(
                        document=document,
                        text=document.content.strip(),
                        position=position,
                        total_chunks=total_chunks,
                        extra_metadata={
                            "structured_row": True,
                            "fila_indice_chunk": position,
                        },
                    )
                )

                tabular_positions[
                    document.doc_id
                ] = (
                    position + 1
                )

                continue

            # ----------------------------------------------------------
            # Documentos narrativos
            # ----------------------------------------------------------

            chunks.extend(
                self.split_document(
                    document
                )
            )

        return chunks