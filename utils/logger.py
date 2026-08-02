"""
Logger centralizado para AD_ASTRA.

Configura un logger con salida a consola y archivo de forma consistente
en todo el proyecto. Importar get_logger() desde cualquier módulo.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from config.settings import LOG_LEVEL, LOG_FILE


def get_logger(name: str = "ad_astra") -> logging.Logger:
    """
    Devuelve un logger configurado con handlers de consola y archivo.

    Si el logger ya tiene handlers configurados, lo devuelve tal cual
    (evita duplicación al importar desde múltiples módulos).

    Args:
        name: Nombre del logger. Se recomienda usar __name__ en cada módulo.

    Returns:
        Instancia de logging.Logger lista para usar.

    Example:
        >>> from utils.logger import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Iniciando pipeline...")
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ── Handler de consola ───────────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # ── Handler de archivo ───────────────────────────────────────────
    try:
        log_path = Path(LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(log_path), encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception:
        # Si no se puede escribir el archivo, solo usamos consola
        pass

    logger.propagate = False
    return logger
