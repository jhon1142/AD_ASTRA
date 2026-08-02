"""
Configuración global del proyecto AD_ASTRA.
"""
from pathlib import Path

# Rutas base
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
MODELS_DIR = BASE_DIR / "models"

# Configuración de loaders
DEFAULT_ENCODING = "utf-8"
REMOTE_TIMEOUT = 30  # segundos

# Configuración de chunking
DEFAULT_CHUNK_SIZE = 512
DEFAULT_CHUNK_OVERLAP = 64

# Configuración de embeddings
EMBEDDING_MODEL = "text-embedding-ada-002"
EMBEDDING_BATCH_SIZE = 32

# Configuración de vectorstore
VECTORSTORE_PATH = DATA_DIR / "vectorstore"

# Configuración de LLM
LLM_MODEL = "gpt-4o"
LLM_TEMPERATURE = 0.0
LLM_MAX_TOKENS = 2048

# Logging
LOG_LEVEL = "INFO"
LOG_FILE = LOGS_DIR / "ad_astra.log"
