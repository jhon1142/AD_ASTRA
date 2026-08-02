"""
Gestión del índice FAISS para AD_ASTRA.

Envuelve faiss con una interfaz simple: add, search, save, load.
Trabaja junto a MetadataStore para recuperar los documentos originales.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from config.settings import VECTORSTORE_PATH


class FAISSManager:
    """
    Administra un índice FAISS de vectores de punto flotante (float32).

    Soporta dos tipos de índice:
    - 'flat_l2'   : Búsqueda exacta por distancia L2. Preciso, lento en escala.
    - 'flat_ip'   : Búsqueda exacta por producto interno (coseno si vectores normalizados).
    - 'ivf_flat'  : Búsqueda aproximada con celdas IVF. Rápido, requiere entrenamiento.

    Args:
        dimensions:  Dimensión de los vectores.
        index_type:  Tipo de índice FAISS ('flat_l2', 'flat_ip', 'ivf_flat').
        nlist:       Número de celdas IVF (solo relevante para 'ivf_flat').
    """

    INDEX_TYPES = ("flat_l2", "flat_ip", "ivf_flat")

    def __init__(
        self,
        dimensions: int,
        index_type: str = "flat_ip",
        nlist: int = 100,
    ) -> None:
        if index_type not in self.INDEX_TYPES:
            raise ValueError(f"index_type debe ser uno de {self.INDEX_TYPES}")
        self.dimensions = dimensions
        self.index_type = index_type
        self.nlist = nlist
        self._index = self._build_index()
        self._trained = index_type not in ("ivf_flat",)  # flat ya está entrenado

    # ------------------------------------------------------------------
    # Construcción del índice
    # ------------------------------------------------------------------

    def _build_index(self):
        try:
            import faiss
        except ImportError as exc:
            raise ImportError("Instala 'faiss-cpu': pip install faiss-cpu") from exc

        if self.index_type == "flat_l2":
            return faiss.IndexFlatL2(self.dimensions)
        if self.index_type == "flat_ip":
            return faiss.IndexFlatIP(self.dimensions)
        if self.index_type == "ivf_flat":
            quantizer = faiss.IndexFlatIP(self.dimensions)
            return faiss.IndexIVFFlat(quantizer, self.dimensions, self.nlist)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    @property
    def size(self) -> int:
        """Número de vectores almacenados en el índice."""
        return self._index.ntotal

    def train(self, vectors: np.ndarray) -> None:
        """
        Entrena el índice IVF. No necesario para índices flat.

        Args:
            vectors: Array numpy float32 de shape (n, dimensions).
        """
        if not self._trained:
            self._index.train(vectors.astype(np.float32))
            self._trained = True

    def add(self, vectors: np.ndarray) -> None:
        """
        Agrega vectores al índice.

        Args:
            vectors: Array numpy float32 de shape (n, dimensions).
        """
        if not self._trained:
            raise RuntimeError("El índice IVF debe ser entrenado antes de agregar vectores.")
        self._index.add(vectors.astype(np.float32))

    def search(self, query: np.ndarray, k: int = 5) -> tuple[np.ndarray, np.ndarray]:
        """
        Busca los k vecinos más cercanos.

        Args:
            query: Vector de consulta de shape (dimensions,) o (1, dimensions).
            k:     Número de resultados a retornar.

        Returns:
            Tupla (distances, indices) — arrays numpy de shape (1, k).
        """
        if query.ndim == 1:
            query = query.reshape(1, -1)
        distances, indices = self._index.search(query.astype(np.float32), k)
        return distances, indices

    def save(self, path: Path | str | None = None) -> Path:
        """
        Guarda el índice en disco.

        Args:
            path: Ruta del archivo. Por defecto usa VECTORSTORE_PATH/faiss.index.

        Returns:
            Ruta donde se guardó el índice.
        """
        import faiss

        save_path = Path(path) if path else Path(VECTORSTORE_PATH) / "faiss.index"
        save_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(save_path))
        return save_path

    @classmethod
    def load(cls, path: Path | str, dimensions: int, index_type: str = "flat_ip") -> "FAISSManager":
        """
        Carga un índice FAISS desde disco.

        Args:
            path:       Ruta al archivo del índice.
            dimensions: Dimensión de los vectores.
            index_type: Tipo de índice (para reconstruir la instancia).

        Returns:
            Instancia de FAISSManager con el índice cargado.
        """
        import faiss

        instance = cls.__new__(cls)
        instance.dimensions = dimensions
        instance.index_type = index_type
        instance.nlist = 100
        instance._trained = True
        instance._index = faiss.read_index(str(path))
        return instance
