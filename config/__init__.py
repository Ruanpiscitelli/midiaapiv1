"""
Módulo de configuração principal.
Exporta todas as configurações de forma organizada.
"""

from .base import base_settings
from .models import models_settings
from .cache import cache_settings, rate_limit_settings
from .minio import MinioSettings

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

# Configurações gerais dos modelos
MODELS_CONFIG = {
    # Hardware e ambiente
    "device": models_settings.device,
    "num_gpus": models_settings.num_gpus,
    "storage_type": models_settings.storage_type,
    
    # Credenciais e tokens
    "hf_token": models_settings.hf_token,
    "api_key": models_settings.api_key,
    "secret_key": models_settings.secret_key,
    
    # Caminhos dos modelos
    "sdxl_model_path": SDXL_CONFIG.model_path,
    "sdxl_local_path": SDXL_CONFIG.local_path,
    "fish_speech_model_path": FISH_SPEECH_CONFIG.model_path,
    "fish_speech_voice_dir": FISH_SPEECH_CONFIG.voice_dir,
    "fish_speech_custom_voice_dir": FISH_SPEECH_CONFIG.custom_voice_dir
}

# Adiciona os caminhos do modelo SDXL
SDXL_MODEL_PATH = SDXL_CONFIG.model_path  # Caminho do modelo online (HuggingFace)
SDXL_LOCAL_PATH = SDXL_CONFIG.local_path  # Caminho local do modelo

# Re-exporta configurações do MinIO
minio_settings = MinioSettings()
MINIO_CONFIG = {
    # Configurações de conexão
    "endpoint": minio_settings.endpoint,
    "access_key": minio_settings.access_key,
    "secret_key": minio_settings.secret_key,
    "secure": minio_settings.secure,
    
    # Configurações de bucket
    "bucket_name": minio_settings.bucket_name,
    "bucket_region": minio_settings.bucket_region,
    
    # Configurações de retry
    "max_retries": minio_settings.max_retries,
    "retry_delay": minio_settings.retry_delay,
    
    # Configurações de timeout
    "connection_timeout": minio_settings.connection_timeout,
    "read_timeout": minio_settings.read_timeout
}

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

# Adicionado para resolver o erro de importação do CELERY_CONFIG
CELERY_CONFIG = {
    "broker_url": "redis://localhost:6379/0",
    "result_backend": "redis://localhost:6379/0",
    "task_serializer": "json",
    "result_serializer": "json",
    "accept_content": ["json"],
    "timezone": "UTC",
    "enable_utc": True
} 