"""
Conteo de tokens para documentos AD_ASTRA.
Soporta tiktoken (OpenAI) con fallback a conteo por palabras.
"""
from __future__ import annotations

from core.document import Document


class TokenCounter:
    """
    Cuenta tokens en un texto usando tiktoken si está disponible,
    o un estimador por palabras como fallback.

    Args:
        model:  Nombre del modelo de OpenAI para seleccionar el encoding
                de tiktoken, e.g. 'gpt-4o', 'text-embedding-ada-002'.
        words_per_token: Factor de conversión palabras→tokens para el fallback.
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        words_per_token: float = 0.75,
    ) -> None:
        self.model = model
        self.words_per_token = words_per_token
        self._encoding = self._load_encoding()

    def _load_encoding(self):
        try:
            import tiktoken
            return tiktoken.encoding_for_model(self.model)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def count(self, text: str) -> int:
        """
        Cuenta los tokens de una cadena.

        Returns:
            Número de tokens (exacto con tiktoken, estimado sin él).
        """
        if self._encoding is not None:
            return len(self._encoding.encode(text))
        # Fallback: estimación por palabras
        words = len(text.split())
        return max(1, int(words / self.words_per_token))

    def count_document(self, document: Document) -> int:
        """Cuenta los tokens del contenido de un Document."""
        return self.count(document.content)

    def fits_in_context(self, text: str, max_tokens: int) -> bool:
        """Retorna True si el texto cabe en el límite de tokens."""
        return self.count(text) <= max_tokens

    def truncate(self, text: str, max_tokens: int) -> str:
        """
        Trunca el texto al número máximo de tokens.

        Returns:
            Texto truncado (decodificado desde tokens si usa tiktoken).
        """
        if self._encoding is not None:
            tokens = self._encoding.encode(text)
            return self._encoding.decode(tokens[:max_tokens])
        # Fallback: truncar por palabras
        max_words = int(max_tokens * self.words_per_token)
        return " ".join(text.split()[:max_words])
