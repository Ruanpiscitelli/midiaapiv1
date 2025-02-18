"""
Módulo de configuração principal.
Exporta todas as configurações de forma organizada.
"""

from .base import base_settings
from .models import models_settings
from .cache import cache_settings, rate_limit_settings
from .minio import minio_settings
from .video import video_settings
from .database import database_settings
from .logging import logging_settings
from .celery import celery_settings

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

# Configurações específicas dos modelos
SDXL_CONFIG = models_settings.get_sdxl_config()
FISH_SPEECH_CONFIG = models_settings.get_fish_speech_config()

# Configuração geral dos modelos (inclui todas as configurações)
MODELS_CONFIG = models_settings.get_config()

# Caminhos específicos dos modelos
SDXL_MODEL_PATH = models_settings.get_sdxl_model_path()
SDXL_LOCAL_PATH = SDXL_CONFIG["local_path"]

# Re-exporta configurações do MinIO
MINIO_CONFIG = minio_settings.get_config()

# Re-exporta configurações de cache
CACHE_CONFIG = cache_settings.get_config()

# Re-exporta configurações de rate limiting
RATE_LIMIT_CONFIG = rate_limit_settings.get_config()

# Re-exporta configurações de vídeo
VIDEO_CONFIG = video_settings.get_config()

# Re-exporta configurações do banco de dados
DATABASE_CONFIG = database_settings.get_config()

# Re-exporta configurações de logging
LOGGING_CONFIG = logging_settings.get_config()

# Re-exporta configurações do Celery
CELERY_CONFIG = celery_settings.get_config()

# Valida diretórios na inicialização
models_settings.validate_paths() 