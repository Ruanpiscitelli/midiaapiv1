"""
Módulo de configuração principal.
Exporta todas as configurações de forma organizada.
"""

from .base import base_settings
from .models import models_settings
from .cache import cache_settings, rate_limit_settings

# Re-exporta configurações principais
API_VERSION = base_settings.API_VERSION
API_TITLE = base_settings.API_TITLE
API_KEY = base_settings.API_KEY
DEBUG = base_settings.DEBUG
ENVIRONMENT = base_settings.ENVIRONMENT

# Re-exporta diretórios
BASE_DIR = base_settings.BASE_DIR
MODELS_DIR = base_settings.MODELS_DIR
TEMP_DIR = base_settings.TEMP_DIR

# Re-exporta configurações de modelos
DEVICE = models_settings.device
NUM_GPUS = models_settings.num_gpus
SDXL_CONFIG = models_settings.sdxl
FISH_SPEECH_CONFIG = models_settings.fish_speech

# Re-exporta configurações de cache
CACHE_CONFIG = {
    "REDIS_URL": cache_settings.REDIS_URL,
    "CACHE_PREFIX": cache_settings.CACHE_PREFIX,
    "TTL": cache_settings.TTL,
    "MAX_SIZE": cache_settings.MAX_SIZE,
    "CACHE_TIMES": cache_settings.CACHE_TIMES,
    "COMPRESSION": {
        "enabled": cache_settings.COMPRESSION_ENABLED,
        "level": cache_settings.COMPRESSION_LEVEL
    },
    "FALLBACK": {
        "enabled": cache_settings.FALLBACK_ENABLED,
        "timeout": cache_settings.FALLBACK_TIMEOUT
    }
}

# Re-exporta configurações de rate limiting
RATE_LIMIT_CONFIG = {
    "enabled": rate_limit_settings.ENABLED,
    "default_limit": rate_limit_settings.DEFAULT_LIMIT,
    "storage_url": rate_limit_settings.STORAGE_URL,
    "limits": rate_limit_settings.LIMITS
}

# Valida diretórios na inicialização
models_settings.validate_paths() 