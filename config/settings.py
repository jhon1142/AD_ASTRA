"""
Configuración global del proyecto AD_ASTRA — Etapa 1.

Encoder + FAISS + Metadata. Sin modelos generativos (LLM).
Lee los valores desde variables de entorno (archivo .env) con
python-dotenv, y define valores por defecto seguros para cada parámetro.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ══════════════════════════════════════════════════════════════════════════════
# Rutas base
# ══════════════════════════════════════════════════════════════════════════════
BASE_DIR = Path(__file__).resolve().parent.parent

# Datos por etapa del pipeline
DATA_DIR       = BASE_DIR / "data"
RAW_DIR        = DATA_DIR / "raw"          # archivos originales sin procesar
PROCESSED_DIR  = DATA_DIR / "processed"   # documentos limpios y normalizados
INDEXES_DIR    = DATA_DIR / "indexes"     # índices FAISS serializados
METADATA_DIR   = DATA_DIR / "metadata"    # MetadataStore (JSON / pickle)

LOGS_DIR   = BASE_DIR / "logs"
MODELS_DIR = BASE_DIR / "models"

# ══════════════════════════════════════════════════════════════════════════════
# Loaders
# ══════════════════════════════════════════════════════════════════════════════
DEFAULT_ENCODING: str = os.getenv("DEFAULT_ENCODING", "utf-8")
REMOTE_TIMEOUT:   int = int(os.getenv("REMOTE_TIMEOUT", "30"))   # segundos

# Formatos de archivo soportados por el sistema
SUPPORTED_FORMATS: list[str] = [
    ".pdf", ".html", ".htm",
    ".json", ".csv", ".xlsx", ".xls",
    ".txt", ".md", ".markdown",
    ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp",
    ".pbf",
]

# ══════════════════════════════════════════════════════════════════════════════
# Idiomas soportados
# ══════════════════════════════════════════════════════════════════════════════
# Códigos ISO 639-1 de los idiomas presentes en el corpus del CODEFEST
SUPPORTED_LANGUAGES: list[str] = ["es", "en", "pt"]

# ══════════════════════════════════════════════════════════════════════════════
# OCR
# ══════════════════════════════════════════════════════════════════════════════
# Idiomas de Tesseract para reconocimiento de texto en imágenes
# Formato: "<lang1>+<lang2>" tal como lo espera pytesseract
OCR_LANGUAGES: str = os.getenv("OCR_LANGUAGES", "spa+eng+por")
OCR_CONFIG:    str = os.getenv("OCR_CONFIG", "--psm 3")   # page segmentation mode

# ══════════════════════════════════════════════════════════════════════════════
# Chunking inteligente
# ══════════════════════════════════════════════════════════════════════════════
# El chunker respeta límites de encoder sin cortar oraciones
CHUNK_SIZE_MIN:    int = int(os.getenv("CHUNK_SIZE_MIN",    "128"))
CHUNK_SIZE_TARGET: int = int(os.getenv("CHUNK_SIZE_TARGET", "512"))
CHUNK_SIZE_MAX:    int = int(os.getenv("CHUNK_SIZE_MAX",    "768"))
CHUNK_OVERLAP:     int = int(os.getenv("CHUNK_OVERLAP",      "64"))

# Aliases de compatibilidad con código existente
DEFAULT_CHUNK_SIZE    = CHUNK_SIZE_TARGET
DEFAULT_CHUNK_OVERLAP = CHUNK_OVERLAP

# ══════════════════════════════════════════════════════════════════════════════
# Embeddings — encoder de Hugging Face (modelo abierto, sin LLM)
# ══════════════════════════════════════════════════════════════════════════════
# Modelos recomendados para el CODEFEST (multilingüe, open-source):
#   - BAAI/bge-m3                         (1024d, multilingüe, estado del arte)
#   - intfloat/multilingual-e5-large      (1024d, multilingüe)
#   - sentence-transformers/paraphrase-multilingual-mpnet-base-v2  (768d)
EMBEDDING_MODEL:      str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
EMBEDDING_BATCH_SIZE: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))
EMBEDDING_NORMALIZE:  bool = os.getenv("EMBEDDING_NORMALIZE", "true").lower() == "true"

# ══════════════════════════════════════════════════════════════════════════════
# FAISS
# ══════════════════════════════════════════════════════════════════════════════
# Tipo de índice por defecto. Opciones: flat_ip | flat_l2 | ivf_flat | hnsw
# flat_ip + normalización = búsqueda por similitud coseno exacta
FAISS_INDEX_TYPE: str  = os.getenv("FAISS_INDEX_TYPE", "flat_ip")
FAISS_NLIST:      int  = int(os.getenv("FAISS_NLIST", "100"))   # solo para ivf_flat

# Alias de compatibilidad
VECTORSTORE_PATH = INDEXES_DIR

# ══════════════════════════════════════════════════════════════════════════════
# Retrieval
# ══════════════════════════════════════════════════════════════════════════════
DEFAULT_TOP_K:    int   = int(os.getenv("DEFAULT_TOP_K", "5"))
SCORE_THRESHOLD:  float = float(os.getenv("SCORE_THRESHOLD", "0.0"))

# ══════════════════════════════════════════════════════════════════════════════
# Logging
# ══════════════════════════════════════════════════════════════════════════════
LOG_LEVEL: str  = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE:  Path = BASE_DIR / os.getenv("LOG_FILE", "logs/ad_astra.log")
