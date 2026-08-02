"""
Utilidades de tokenización para AD_ASTRA.

Envuelve tiktoken con una interfaz simple y un fallback por palabras.
Usado por chunking y embeddings para contar y truncar tokens.
"""
from __future__ import annotations

from config.settings import EMBEDDING_MODEL


class Tokenizer:
    """
    Wrapper de tiktoken con fallback a tokenización por palabras.

    Args:
        model:           Modelo de OpenAI para seleccionar el encoding tiktoken.
        words_per_token: Factor de conversión palabras→tokens para el fallback.
    """

    def __init__(
        self,
        model: str = EMBEDDING_MODEL,
        words_per_token: float = 0.75,
    ) -> None:
        self.model = model
        self.words_per_token = words_per_token
        self._enc = self._load(model)

    @staticmethod
    def _load(model: str):
        try:
            import tiktoken
            return tiktoken.encoding_for_model(model)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Tokenización
    # ------------------------------------------------------------------

    def encode(self, text: str) -> list[int]:
        """
        Convierte texto en lista de IDs de tokens.

        Returns:
            Lista de enteros (tokens). Con fallback, cada palabra es un token.
        """
        if self._enc:
            return self._enc.encode(text)
        return list(range(len(text.split())))

    def decode(self, tokens: list[int]) -> str:
        """
        Convierte lista de IDs de tokens en texto.

        Returns:
            Texto decodificado. Con fallback devuelve string vacío.
        """
        if self._enc:
            return self._enc.decode(tokens)
        return ""

    def count(self, text: str) -> int:
        """Cuenta los tokens de un texto."""
        if self._enc:
            return len(self._enc.encode(text))
        return max(1, int(len(text.split()) / self.words_per_token))

    def truncate(self, text: str, max_tokens: int) -> str:
        """
        Trunca el texto al número máximo de tokens.

        Args:
            text:       Texto a truncar.
            max_tokens: Límite de tokens.

        Returns:
            Texto truncado, decodificado desde tokens.
        """
        if self._enc:
            tokens = self._enc.encode(text)
            return self._enc.decode(tokens[:max_tokens])
        max_words = int(max_tokens * self.words_per_token)
        return " ".join(text.split()[:max_words])

    def fits(self, text: str, max_tokens: int) -> bool:
        """Retorna True si el texto cabe dentro de max_tokens."""
        return self.count(text) <= max_tokens

    # ------------------------------------------------------------------
    # Batch
    # ------------------------------------------------------------------

    def count_many(self, texts: list[str]) -> list[int]:
        """Cuenta tokens de una lista de textos."""
        return [self.count(t) for t in texts]

    def filter_by_length(
        self,
        texts: list[str],
        min_tokens: int = 1,
        max_tokens: int = 8191,
    ) -> list[str]:
        """
        Filtra textos que estén fuera del rango de tokens.

        Args:
            texts:      Lista de textos.
            min_tokens: Mínimo de tokens (inclusivo).
            max_tokens: Máximo de tokens (inclusivo).

        Returns:
            Lista de textos dentro del rango.
        """
        return [t for t in texts if min_tokens <= self.count(t) <= max_tokens]
