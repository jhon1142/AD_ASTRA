"""
Limpieza y normalización de texto para documentos AD_ASTRA.
"""
import re
import unicodedata

from core.document import Document


class TextCleaner:
    """
    Aplica una serie de transformaciones de limpieza sobre el contenido
    de un Document.

    Pasos disponibles (todos activos por defecto):
    - normalize_unicode: convierte a NFC y elimina caracteres de control.
    - remove_extra_whitespace: colapsa espacios y líneas en blanco múltiples.
    - remove_urls: elimina URLs http/https.
    - remove_emails: elimina direcciones de correo.
    - lowercase: convierte a minúsculas.
    """

    def __init__(
        self,
        normalize_unicode: bool = True,
        remove_extra_whitespace: bool = True,
        remove_urls: bool = False,
        remove_emails: bool = False,
        lowercase: bool = False,
    ) -> None:
        self.normalize_unicode = normalize_unicode
        self.remove_extra_whitespace = remove_extra_whitespace
        self.remove_urls = remove_urls
        self.remove_emails = remove_emails
        self.lowercase = lowercase

    # ------------------------------------------------------------------
    # Métodos individuales de limpieza
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_unicode(text: str) -> str:
        text = unicodedata.normalize("NFC", text)
        # Elimina caracteres de control excepto \n y \t
        return "".join(ch for ch in text if unicodedata.category(ch) != "Cc" or ch in "\n\t")

    @staticmethod
    def _remove_extra_whitespace(text: str) -> str:
        # Colapsa espacios múltiples en uno
        text = re.sub(r"[ \t]+", " ", text)
        # Colapsa líneas en blanco múltiples en dos saltos
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def _remove_urls(text: str) -> str:
        return re.sub(r"https?://\S+", "", text)

    @staticmethod
    def _remove_emails(text: str) -> str:
        return re.sub(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", "", text)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def clean_text(self, text: str) -> str:
        """Aplica el pipeline de limpieza a una cadena de texto."""
        if self.normalize_unicode:
            text = self._normalize_unicode(text)
        if self.remove_urls:
            text = self._remove_urls(text)
        if self.remove_emails:
            text = self._remove_emails(text)
        if self.lowercase:
            text = text.lower()
        if self.remove_extra_whitespace:
            text = self._remove_extra_whitespace(text)
        return text

    def clean(self, document: Document) -> Document:
        """
        Devuelve un nuevo Document con el contenido limpio.
        Los metadatos originales se conservan.
        """
        return Document(
            doc_id=document.doc_id,
            fuente=document.fuente,
            formato=document.formato,
            fenomeno=document.fenomeno,
            content=self.clean_text(document.content),
            metadata={
                **document.metadata,
                "cleaned": True,
            },
        )

    def clean_many(self, documents: list[Document]) -> list[Document]:
        """Aplica clean() a una lista de documentos."""
        return [self.clean(doc) for doc in documents]
