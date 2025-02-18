"""
Módulo de configuração principal.
Exporta todas as configurações de forma organizada.
"""

import os
import torch
from pathlib import Path

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
MINIO_CONFIG = minio_settings.get_config()

# Re-exporta configurações de cache
CACHE_CONFIG = {
    "REDIS_URL": "redis://localhost:6379/0",
    "CACHE_PREFIX": "midia_api_cache",
    "TTL": 3600,  # 1 hora
    "CACHE_TIMES": {
        "status": 60,  # 1 minuto
        "health": 300,  # 5 minutos
        "voices": 3600  # 1 hora
    }
}

# Re-exporta configurações de rate limiting
RATE_LIMIT_CONFIG = {
    "enabled": True,
    "default_limit": "100/minute",
    "generate_video": "10/minute",
    "generate_image": "20/minute",
    "generate_tts": "30/minute",
    "clone_voice": "5/minute",
    "status": "200/minute",
    "voices": "100/minute",
    "health": "100/minute"
}

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

# Diretórios base
BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"
TEMP_DIR = BASE_DIR / "temp"

# Configurações de hardware
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
NUM_GPUS = torch.cuda.device_count() if torch.cuda.is_available() else 0

# Configurações de modelos
MODELS_CONFIG = models_settings.get_config()
SDXL_CONFIG = models_settings.get_sdxl_config()
FISH_SPEECH_CONFIG = models_settings.get_fish_speech_config()
SDXL_MODEL_PATH = models_settings.get_sdxl_model_path()

# Configurações do MinIO
MINIO_CONFIG = minio_settings.get_config()

# Configurações de Celery
CELERY_CONFIG = celery_settings.get_config()

# Configurações de cache
CACHE_CONFIG = {
    "REDIS_URL": "redis://localhost:6379/0",
    "CACHE_PREFIX": "midia_api_cache",
    "TTL": 3600,  # 1 hora
    "CACHE_TIMES": {
        "status": 60,  # 1 minuto
        "health": 300,  # 5 minutos
        "voices": 3600  # 1 hora
    }
}

# Configurações de rate limit
RATE_LIMIT_CONFIG = {
    "enabled": True,
    "default_limit": "100/minute",
    "generate_video": "10/minute",
    "generate_image": "20/minute",
    "generate_tts": "30/minute",
    "clone_voice": "5/minute",
    "status": "200/minute",
    "voices": "100/minute",
    "health": "100/minute"
}

# Configurações da API
API_VERSION = "2.0"
API_TITLE = "Gerador de Vídeos com IA"
API_KEY = os.getenv("API_KEY", "minha-chave-api")
DEBUG = os.getenv("DEBUG", "False").lower() == "true" 