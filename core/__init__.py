# core/ ahora es un alias de models/ para compatibilidad con código existente.
# Importar siempre desde models/ directamente.
from models.document import Document

__all__ = ["Document"]
