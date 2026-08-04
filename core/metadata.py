"""
Modelo de metadata extendida para AD_ASTRA — CODEFEST 2026.

Centraliza los campos opcionales que el equipo puede añadir a cada chunk
más allá de los obligatorios definidos en la Tabla 1 del spec.

Ref: Sección 3.4 — "Los equipos pueden añadir campos adicionales".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChunkMetadata:
    """
    Campos de metadata extendida opcionales por fragmento.

    Todos son opcionales. Se serializan junto con los campos obligatorios
    en el metadata.jsonl de entrega.

    Attributes:
        idioma:            Código ISO 639-1 detectado ('es', 'en', 'pt').
        titulo:            Título del documento de origen, si está disponible.
        fecha_publicacion: Fecha de publicación del documento (ISO 8601).
        url:               URL de origen, si el documento fue descargado.
        seccion:           Título de la sección o encabezado del chunk.
        pagina:            Número de página de origen (para PDFs).
        cleaned:           Si el texto fue limpiado por el preprocesador.
        normalized:        Si el texto fue normalizado.
        ocr:               Si el texto fue extraído mediante OCR.
        extra:             Cualquier campo adicional no previsto.
    """
    idioma:             str = ""
    titulo:             str = ""
    fecha_publicacion:  str = ""
    url:                str = ""
    seccion:            str = ""
    pagina:             int = -1
    cleaned:            bool = False
    normalized:         bool = False
    ocr:                bool = False
    extra:              dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serializa solo los campos con valor no vacío / no por defecto."""
        result: dict[str, Any] = {}
        if self.idioma:
            result["idioma"] = self.idioma
        if self.titulo:
            result["titulo"] = self.titulo
        if self.fecha_publicacion:
            result["fecha_publicacion"] = self.fecha_publicacion
        if self.url:
            result["url"] = self.url
        if self.seccion:
            result["seccion"] = self.seccion
        if self.pagina >= 0:
            result["pagina"] = self.pagina
        if self.cleaned:
            result["cleaned"] = self.cleaned
        if self.normalized:
            result["normalized"] = self.normalized
        if self.ocr:
            result["ocr"] = self.ocr
        result.update(self.extra)
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChunkMetadata":
        """Reconstruye desde un diccionario de metadatos."""
        known = {
            "idioma", "titulo", "fecha_publicacion", "url",
            "seccion", "pagina", "cleaned", "normalized", "ocr",
        }
        extra = {k: v for k, v in data.items() if k not in known}
        return cls(
            idioma            = data.get("idioma", ""),
            titulo            = data.get("titulo", ""),
            fecha_publicacion = data.get("fecha_publicacion", ""),
            url               = data.get("url", ""),
            seccion           = data.get("seccion", ""),
            pagina            = int(data.get("pagina", -1)),
            cleaned           = bool(data.get("cleaned", False)),
            normalized        = bool(data.get("normalized", False)),
            ocr               = bool(data.get("ocr", False)),
            extra             = extra,
        )
