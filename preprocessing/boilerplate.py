"""
Eliminación de texto repetitivo (boilerplate) en documentos AD_ASTRA.

Boilerplate típico: headers/footers de PDF, disclaimers legales,
firmas de correo, textos de copyright, etc.
"""
import re
from collections import Counter

from core.document import Document


class BoilerplateRemover:
    """
    Detecta y elimina fragmentos de texto boilerplate de los documentos.

    Estrategias disponibles:
    - patterns:    Elimina líneas que coincidan con expresiones regulares.
    - frequency:   Elimina líneas que aparecen en más del `freq_threshold`
                   de los documentos (requiere llamar a fit() primero).

    Args:
        patterns:        Lista de regex. Las líneas que coincidan se eliminan.
        freq_threshold:  Fracción [0-1] de documentos en que debe aparecer
                         una línea para considerarla boilerplate.
        use_frequency:   Activar detección por frecuencia.
        min_line_length: Líneas más cortas que esto se ignoran en el análisis
                         de frecuencia.
    """

    # Patrones por defecto: números de página, URLs, emails genéricos, etc.
    DEFAULT_PATTERNS: list[str] = [
        r"^\s*página\s+\d+\s*$",
        r"^\s*page\s+\d+\s*(of\s+\d+)?\s*$",
        r"^\s*\d+\s*$",                          # solo un número
        r"^confidential(ity notice)?.*$",
        r"^este (mensaje|correo).*confidencial.*$",
        r"^all rights reserved.*$",
        r"^copyright\s+©?\s*\d{4}.*$",
        r"^www\.[^\s]+$",
    ]

    def __init__(
        self,
        patterns: list[str] | None = None,
        freq_threshold: float = 0.5,
        use_frequency: bool = False,
        min_line_length: int = 10,
    ) -> None:
        raw_patterns = (patterns or []) + self.DEFAULT_PATTERNS
        self._compiled = [re.compile(p, re.IGNORECASE) for p in raw_patterns]
        self.freq_threshold = freq_threshold
        self.use_frequency = use_frequency
        self.min_line_length = min_line_length
        self._frequent_lines: set[str] = set()

    # ------------------------------------------------------------------
    # Detección por frecuencia
    # ------------------------------------------------------------------

    def fit(self, documents: list[Document]) -> "BoilerplateRemover":
        """
        Analiza una colección de documentos para detectar líneas frecuentes.

        Args:
            documents: Corpus completo de documentos.

        Returns:
            self (permite encadenamiento).
        """
        total = len(documents)
        if total == 0:
            return self

        line_doc_count: Counter = Counter()
        for doc in documents:
            seen_in_doc = set()
            for line in doc.content.splitlines():
                line = line.strip()
                if len(line) >= self.min_line_length:
                    seen_in_doc.add(line.lower())
            line_doc_count.update(seen_in_doc)

        self._frequent_lines = {
            line
            for line, count in line_doc_count.items()
            if count / total >= self.freq_threshold
        }
        return self

    # ------------------------------------------------------------------
    # Limpieza
    # ------------------------------------------------------------------

    def _is_boilerplate_line(self, line: str) -> bool:
        stripped = line.strip()
        if any(p.match(stripped) for p in self._compiled):
            return True
        if self.use_frequency and stripped.lower() in self._frequent_lines:
            return True
        return False

    def remove(self, document: Document) -> Document:
        """Devuelve un nuevo Document sin líneas boilerplate."""
        clean_lines = [
            line for line in document.content.splitlines()
            if not self._is_boilerplate_line(line)
        ]
        return Document(
            content="\n".join(clean_lines),
            metadata={**document.metadata, "boilerplate_removed": True},
            doc_id=document.doc_id,
        )

    def remove_many(self, documents: list[Document]) -> list[Document]:
        """Aplica remove() a una lista de documentos."""
        return [self.remove(doc) for doc in documents]
