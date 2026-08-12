"""
Normalización de texto para documentos AD_ASTRA.

Complementa a TextCleaner con transformaciones más específicas:
números, fechas, abreviaciones, caracteres especiales, etc.
"""
import re
import unicodedata

from core.document import Document


class TextNormalizer:
    """
    Aplica normalizaciones estructurales al texto de un Document.

    Pasos configurables:
    - expand_contractions:  Expande contracciones del español/inglés básicas.
    - normalize_numbers:    Reemplaza secuencias de dígitos por <NUM>.
    - normalize_dates:      Reemplaza patrones de fecha por <DATE>.
    - remove_punctuation:   Elimina signos de puntuación (conserva letras y números).
    - strip_accents:        Elimina tildes y diacríticos.
    - fix_encoding_errors:  Corrige errores típicos de encoding (mojibake).
    """

    # Correcciones de encoding frecuentes (UTF-8 mal interpretado como latin-1)
    ENCODING_FIXES: dict[str, str] = {
        "Ã¡": "á", "Ã©": "é", "Ã­": "í", "Ã³": "ó", "Ãº": "ú",
        "Ã±": "ñ", "Ã\x81": "Á", "Ã‰": "É", "Ã\x8d": "Í",
        "Ã": "Ó", "Ãš": "Ú", "Ã'": "Ñ", "Â¿": "¿", "Â¡": "¡",
    }

    # Contracciones básicas en inglés
    CONTRACTIONS: dict[str, str] = {
        r"\bdon't\b": "do not", r"\bcan't\b": "cannot",
        r"\bwon't\b": "will not", r"\bI'm\b": "I am",
        r"\bI've\b": "I have", r"\bI'll\b": "I will",
        r"\bI'd\b": "I would", r"\bit's\b": "it is",
        r"\bhe's\b": "he is", r"\bshe's\b": "she is",
        r"\bthey're\b": "they are", r"\bwe're\b": "we are",
    }

    def __init__(
        self,
        expand_contractions: bool = False,
        normalize_numbers: bool = False,
        normalize_dates: bool = False,
        remove_punctuation: bool = False,
        strip_accents: bool = False,
        fix_encoding_errors: bool = True,
    ) -> None:
        self.expand_contractions = expand_contractions
        self.normalize_numbers = normalize_numbers
        self.normalize_dates = normalize_dates
        self.remove_punctuation = remove_punctuation
        self.strip_accents = strip_accents
        self.fix_encoding_errors = fix_encoding_errors

        # Patrón de fechas: dd/mm/yyyy, yyyy-mm-dd, dd de mes de yyyy
        self._date_pattern = re.compile(
            r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{2}[/-]\d{2}"
            r"|\d{1,2}\s+de\s+\w+\s+de\s+\d{4})\b",
            re.IGNORECASE,
        )

    # ------------------------------------------------------------------
    # Pasos individuales
    # ------------------------------------------------------------------

    def _fix_encoding(self, text: str) -> str:
        for bad, good in self.ENCODING_FIXES.items():
            text = text.replace(bad, good)
        return text

    def _expand_contractions(self, text: str) -> str:
        for pattern, replacement in self.CONTRACTIONS.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text

    @staticmethod
    def _normalize_numbers(text: str) -> str:
        return re.sub(r"\b\d+([.,]\d+)*\b", "<NUM>", text)

    def _normalize_dates(self, text: str) -> str:
        return self._date_pattern.sub("<DATE>", text)

    @staticmethod
    def _remove_punctuation(text: str) -> str:
        return re.sub(r"[^\w\s]", " ", text)

    @staticmethod
    def _strip_accents(text: str) -> str:
        nfkd = unicodedata.normalize("NFKD", text)
        return "".join(c for c in nfkd if not unicodedata.combining(c))

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def normalize_text(self, text: str) -> str:
        """Aplica el pipeline de normalización a una cadena."""
        if self.fix_encoding_errors:
            text = self._fix_encoding(text)
        if self.expand_contractions:
            text = self._expand_contractions(text)
        if self.normalize_dates:
            text = self._normalize_dates(text)
        if self.normalize_numbers:
            text = self._normalize_numbers(text)
        if self.remove_punctuation:
            text = self._remove_punctuation(text)
        if self.strip_accents:
            text = self._strip_accents(text)
        return text

    def normalize(self, document: Document) -> Document:
        """Devuelve un nuevo Document con el contenido normalizado."""
        return Document(
            content=self.normalize_text(document.content),
            metadata={**document.metadata, "normalized": True},
            doc_id=document.doc_id,
        )

    def normalize_many(self, documents: list[Document]) -> list[Document]:
        """Aplica normalize() a una lista de documentos."""
        return [self.normalize(doc) for doc in documents]
