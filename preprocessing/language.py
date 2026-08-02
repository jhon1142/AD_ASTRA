"""
Detección de idioma para documentos AD_ASTRA.
Requiere: langdetect
"""
from core.document import Document


class LanguageDetector:
    """
    Detecta el idioma del contenido de un Document y lo agrega a los metadatos.

    Args:
        field:        Nombre del campo de metadatos donde se guarda el idioma.
        min_chars:    Mínimo de caracteres necesarios para intentar detección.
        fallback:     Valor por defecto si la detección falla.
    """

    def __init__(
        self,
        field: str = "language",
        min_chars: int = 20,
        fallback: str = "unknown",
    ) -> None:
        self.field = field
        self.min_chars = min_chars
        self.fallback = fallback

    def detect(self, text: str) -> str:
        """
        Detecta el idioma de una cadena de texto.

        Returns:
            Código ISO 639-1 del idioma (ej. 'es', 'en') o el fallback.
        """
        if len(text.strip()) < self.min_chars:
            return self.fallback
        try:
            from langdetect import detect
            return detect(text)
        except Exception:
            return self.fallback

    def tag(self, document: Document) -> Document:
        """
        Devuelve un nuevo Document con el idioma detectado en sus metadatos.
        """
        lang = self.detect(document.content)
        return Document(
            content=document.content,
            metadata={**document.metadata, self.field: lang},
            doc_id=document.doc_id,
        )

    def tag_many(self, documents: list[Document]) -> list[Document]:
        """Aplica tag() a una lista de documentos."""
        return [self.tag(doc) for doc in documents]

    def filter_by_language(
        self,
        documents: list[Document],
        languages: list[str],
    ) -> list[Document]:
        """
        Filtra documentos que no pertenecen a los idiomas indicados.

        Args:
            documents: Lista de Documents (deben tener metadato de idioma).
            languages: Lista de códigos ISO 639-1 a conservar, ej. ['es', 'en'].

        Returns:
            Documentos cuyo idioma detectado está en la lista.
        """
        tagged = self.tag_many(documents)
        return [doc for doc in tagged if doc.metadata.get(self.field) in languages]
