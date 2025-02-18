"""
Módulo de configuração principal.
Exporta todas as configurações de forma organizada.
"""

from .base import base_settings
from .models import models_settings
from .cache import cache_settings, rate_limit_settings
from .minio import MinioSettings
from .video import video_settings
from .database import database_settings

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

# Re-exporta configurações de vídeo
VIDEO_CONFIG = {
    # Diretórios
    "temp_dir": video_settings.temp_dir,
    "output_dir": video_settings.output_dir,
    "assets_dir": video_settings.assets_dir,
    
    # Configurações de vídeo
    "width": video_settings.width,
    "height": video_settings.height,
    "fps": video_settings.fps,
    "bitrate": video_settings.bitrate,
    
    # Configurações de codecs
    "video_codec": video_settings.video_codec,
    "audio_codec": video_settings.audio_codec,
    "pixel_format": video_settings.pixel_format,
    
    # Configurações de qualidade
    "crf": video_settings.crf,
    "preset": video_settings.preset,
    
    # Configurações de áudio
    "audio_bitrate": video_settings.audio_bitrate,
    "audio_sample_rate": video_settings.audio_sample_rate,
    
    # Configurações de transições
    "transition_duration": video_settings.transition_duration,
    "default_transition": video_settings.default_transition,
    "available_transitions": video_settings.available_transitions,
    
    # Configurações de efeitos
    "effects_enabled": video_settings.effects_enabled,
    "max_effects_per_scene": video_settings.max_effects_per_scene,
    "available_effects": video_settings.available_effects,
    
    # Configurações de renderização
    "max_scenes": video_settings.max_scenes,
    "max_duration": video_settings.max_duration,
    "max_file_size": video_settings.max_file_size,
    
    # Configurações de threads
    "threads": video_settings.threads
}

# Re-exporta configurações do banco de dados
DATABASE_CONFIG = {
    # Configurações de conexão
    "host": database_settings.host,
    "port": database_settings.port,
    "database": database_settings.database,
    "username": database_settings.username,
    "password": database_settings.password,
    "url": database_settings.url,
    
    # Configurações do pool
    "pool_size": database_settings.pool_size,
    "max_overflow": database_settings.max_overflow,
    "pool_timeout": database_settings.pool_timeout,
    "pool_recycle": database_settings.pool_recycle,
    
    # Configurações de timeout
    "connect_timeout": database_settings.connect_timeout,
    "command_timeout": database_settings.command_timeout,
    
    # Configurações de SSL
    "ssl_mode": database_settings.ssl_mode,
    "ssl_cert": database_settings.ssl_cert,
    
    # Configurações de debug
    "echo": database_settings.echo,
    "echo_pool": database_settings.echo_pool
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