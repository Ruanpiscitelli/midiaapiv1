"""
Configuração de cache para a aplicação.
"""

import os

# Configurações do Redis
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# URL do Redis
REDIS_URL = (
    f"redis://{':' + REDIS_PASSWORD + '@' if REDIS_PASSWORD else ''}"
    f"{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
)

# Prefixo para as chaves de cache
CACHE_PREFIX = "api-cache:"

# Tempos de expiração (em segundos)
CACHE_TIMES = {
    "status": 30,        # Status de jobs
    "voices": 3600,      # Lista de vozes disponíveis
    "health": 60,        # Health check
    "metrics": 300,      # Métricas do sistema
    "config": 1800,      # Configurações
    "templates": 7200    # Templates de vídeo
}

# Configurações de compressão
CACHE_COMPRESSION = True
CACHE_COMPRESSION_LEVEL = 6  # 1-9, onde 9 é máxima compressão

# Configurações de fallback
CACHE_FALLBACK_ENABLED = True
CACHE_FALLBACK_TIMEOUT = 5  # segundos

# Configurações de invalidação
CACHE_INVALIDATION_PATTERNS = {
    "status": "status:*",
    "voices": "voices:*",
    "health": "health:*",
    "metrics": "metrics:*",
    "config": "config:*",
    "templates": "templates:*"
}

# Configurações de backup
CACHE_BACKUP_ENABLED = True
CACHE_BACKUP_INTERVAL = 3600  # 1 hora
CACHE_BACKUP_PATH = "cache_backup/"

# Configurações de monitoramento
CACHE_MONITOR_ENABLED = True
CACHE_MONITOR_INTERVAL = 60  # 1 minuto

# Configurações de rate limiting
RATE_LIMIT_ENABLED = True
RATE_LIMIT_DEFAULT = "100/minute"
RATE_LIMITS = {
    "generate_video": "10/minute",
    "generate_image": "20/minute",
    "generate_tts": "30/minute",
    "status": "100/minute",
    "health": "100/minute"
} 