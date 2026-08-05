"""
Parser para archivos PBF (OpenStreetMap .osm.pbf).

El spec indica: recorrer las capas, leer los atributos de cada elemento
del mapa y pasarlos a texto como pares "atributo: valor". Conservar
una sola versión por elemento para no duplicar datos.

Requiere: pyosmium → pip install osmium
"""
from __future__ import annotations

from pathlib import Path
from typing import Union

from core.document import Document
from data.parsers.base_loader import BaseLoader, infer_fenomeno, make_doc_id


class PBFLoader(BaseLoader):
    """
    Extrae entidades de un archivo PBF de OpenStreetMap.

    Produce un Document por entidad (nodo/vía/relación) con nombre,
    formateando sus atributos como "atributo: valor".

    Args:
        entity_types: Tipos a extraer. None = ['node', 'way', 'relation'].
        only_named:   Si True, omite entidades sin atributo 'name'.
    """

    def __init__(
        self,
        entity_types: list[str] | None = None,
        only_named: bool = True,
    ) -> None:
        self.entity_types = set(entity_types or ["node", "way", "relation"])
        self.only_named   = only_named

    def load(self, source: Union[str, Path]) -> list[Document]:
        try:
            import osmium
        except ImportError as exc:
            raise ImportError("Instala 'osmium': pip install osmium") from exc

        path     = Path(source)
        doc_base = make_doc_id(path)
        fenomeno = infer_fenomeno(path)

        collector = _EntityCollector(
            entity_types = self.entity_types,
            only_named   = self.only_named,
            doc_base     = doc_base,
            fuente       = path.name,
            fenomeno     = fenomeno,
            path_str     = str(path),
        )
        collector.apply_file(str(path))
        return collector.documents


class _EntityCollector:
    """Recolecta entidades OSM y las convierte en Documents."""

    def __init__(
        self,
        entity_types: set[str],
        only_named: bool,
        doc_base: str,
        fuente: str,
        fenomeno: int,
        path_str: str,
    ) -> None:
        self.entity_types = entity_types
        self.only_named   = only_named
        self.doc_base     = doc_base
        self.fuente       = fuente
        self.fenomeno     = fenomeno
        self.path_str     = path_str
        self.documents: list[Document] = []
        self._seen_ids: set[str] = set()   # evitar duplicados

    def apply_file(self, path: str) -> None:
        import osmium

        parent = self

        class _Handler(osmium.SimpleHandler):
            def node(self, n):
                if "node" not in parent.entity_types:
                    return
                parent._process(
                    entity_type = "node",
                    osm_id      = n.id,
                    tags        = dict(n.tags),
                    extra       = {
                        "lat": n.location.lat if n.location.valid() else None,
                        "lon": n.location.lon if n.location.valid() else None,
                    },
                )

            def way(self, w):
                if "way" not in parent.entity_types:
                    return
                parent._process("way", w.id, dict(w.tags))

            def relation(self, r):
                if "relation" not in parent.entity_types:
                    return
                parent._process("relation", r.id, dict(r.tags))

        h = _Handler()
        h.apply_file(path)

    def _process(
        self,
        entity_type: str,
        osm_id: int,
        tags: dict,
        extra: dict | None = None,
    ) -> None:
        uid = f"{entity_type}:{osm_id}"
        if uid in self._seen_ids:
            return
        self._seen_ids.add(uid)

        name = tags.get("name", "").strip()
        if self.only_named and not name:
            return

        # Formatear atributos como "atributo: valor"
        parts = [f"{k}: {v}" for k, v in tags.items() if v]
        content = name if name else f"{entity_type} {osm_id}"
        if parts:
            content += "\n" + " | ".join(parts)

        meta = {
            "ruta_completa": self.path_str,
            "tipo_entidad": entity_type,
            "osm_id": osm_id,
        }
        if extra:
            meta.update({k: v for k, v in extra.items() if v is not None})

        self.documents.append(
            Document(
                doc_id   = f"{self.doc_base}_{entity_type}_{osm_id}",
                fuente   = self.fuente,
                formato  = "pbf",
                fenomeno = self.fenomeno,
                content  = content,
                metadata = meta,
            )
        )
