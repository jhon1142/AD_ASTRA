"""
Loader para archivos PBF (Protocol Buffer Binary Format).

Usado principalmente con datos geoespaciales OpenStreetMap (.osm.pbf).
Requiere: osmium (pyosmium) para OSM o protobuf para formatos genéricos.

Si el formato PBF que usas no es OSM, ajusta el método `load` según
la librería específica de tu dominio.
"""
from pathlib import Path
from typing import Union

from core.document import Document
from data.loaders.base_loader import BaseLoader


class PBFLoader(BaseLoader):
    """
    Carga datos de archivos PBF (OpenStreetMap) y extrae entidades
    (nodos, vías, relaciones) como Documents.

    Requiere: pyosmium  →  pip install osmium
    """

    def __init__(self, entity_types: list[str] | None = None) -> None:
        """
        Args:
            entity_types: Lista de tipos a extraer: ['node', 'way', 'relation'].
                          None = todos.
        """
        self.entity_types = entity_types or ["node", "way", "relation"]

    def load(self, source: Union[str, Path]) -> list[Document]:
        try:
            import osmium
        except ImportError as exc:
            raise ImportError("Instala 'osmium': pip install osmium") from exc

        path = Path(source)
        handler = _OSMHandler(entity_types=self.entity_types)
        handler.apply_file(str(path))

        return handler.documents


class _OSMHandler:
    """Handler interno de osmium para recolectar entidades."""

    def __init__(self, entity_types: list[str]) -> None:
        self.entity_types = entity_types
        self.documents: list[Document] = []

    def apply_file(self, path: str) -> None:
        import osmium

        class _Inner(osmium.SimpleHandler):
            def __init__(inner_self) -> None:
                super().__init__()
                inner_self.docs: list[Document] = []

            def node(inner_self, n) -> None:
                if "node" not in self.entity_types:
                    return
                tags = dict(n.tags)
                content = tags.get("name", f"node:{n.id}")
                inner_self.docs.append(
                    Document(
                        content=content,
                        metadata={
                            "source": path,
                            "file_type": "pbf",
                            "entity_type": "node",
                            "osm_id": n.id,
                            "lat": n.location.lat if n.location.valid() else None,
                            "lon": n.location.lon if n.location.valid() else None,
                            **tags,
                        },
                    )
                )

            def way(inner_self, w) -> None:
                if "way" not in self.entity_types:
                    return
                tags = dict(w.tags)
                content = tags.get("name", f"way:{w.id}")
                inner_self.docs.append(
                    Document(
                        content=content,
                        metadata={
                            "source": path,
                            "file_type": "pbf",
                            "entity_type": "way",
                            "osm_id": w.id,
                            **tags,
                        },
                    )
                )

            def relation(inner_self, r) -> None:
                if "relation" not in self.entity_types:
                    return
                tags = dict(r.tags)
                content = tags.get("name", f"relation:{r.id}")
                inner_self.docs.append(
                    Document(
                        content=content,
                        metadata={
                            "source": path,
                            "file_type": "pbf",
                            "entity_type": "relation",
                            "osm_id": r.id,
                            **tags,
                        },
                    )
                )

        h = _Inner()
        h.apply_file(path)
        self.documents = h.docs
