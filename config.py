"""
Configurações globais do projeto.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import logging.config
import torch

# Carrega variáveis de ambiente
load_dotenv()

# Configurações de logging melhoradas
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        },
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": "INFO"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "app.log",
            "formatter": "detailed",
            "level": "DEBUG",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "error.log",
            "formatter": "detailed",
            "level": "ERROR",
            "maxBytes": 10485760,
            "backupCount": 5
        }
    },
    "loggers": {
        "api": {
            "handlers": ["console", "file", "error_file"],
            "level": "INFO",
            "propagate": False
        },
        "storage": {
            "handlers": ["console", "file", "error_file"],
            "level": "INFO",
            "propagate": False
        },
        "tasks": {
            "handlers": ["console", "file", "error_file"],
            "level": "INFO",
            "propagate": False
        }
    },
    "root": {
        "handlers": ["console", "file", "error_file"],
        "level": "INFO"
    }
}

# Configura logging
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# Diretórios base
BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"
TEMP_DIR = BASE_DIR / "temp"

# Caminhos específicos
SDXL_LOCAL_PATH = MODELS_DIR / "sdxl"
SDXL_MODEL_PATH = os.getenv("SDXL_MODEL_PATH", "stabilityai/stable-diffusion-xl-base-1.0")
VIDEO_TEMP_DIR = TEMP_DIR / "video"
FISH_SPEECH_MODEL_PATH = MODELS_DIR / "fish_speech"

# Configurações da API
API_VERSION = "2.0"
API_TITLE = "Gerador de Vídeos com IA"
API_KEY = os.getenv("API_KEY", "minha-chave-api")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Configurações de hardware
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
NUM_GPUS = torch.cuda.device_count() if torch.cuda.is_available() else 0

# Configurações do MinIO
MINIO_CONFIG = {
    # Endpoint principal
    "api_base_url": "https://minio.ruanpiscitelli.com/api/v1",
    "service_account_url": "https://minio.ruanpiscitelli.com/api/v1/service-account-credentials",
    
    # Configurações de conexão
    "endpoint": "minio.ruanpiscitelli.com",  # Sem protocolo
    "region": "us-east-1",  # Região padrão
    "secure": True,  # Sempre usar HTTPS
    
    # Credenciais (serão atualizadas via API)
    "access_key": os.getenv("MINIO_ACCESS_KEY", ""),
    "secret_key": os.getenv("MINIO_SECRET_KEY", ""),
    "session_token": os.getenv("MINIO_SESSION_TOKEN", ""),
    
    # Configurações do bucket
    "bucket_name": os.getenv("MINIO_BUCKET", "media-bucket"),
    "bucket_region": os.getenv("MINIO_REGION", "us-east-1"),
    
    # URLs públicas
    "public_url_base": "https://minio.ruanpiscitelli.com/api/v1",
    
    # Configurações de retry e timeout
    "max_retries": 3,
    "retry_delay": 1,
    "timeout": 30,
    "connection_timeout": 10,
    
    # Cache de credenciais
    "credentials_cache_time": 3600,  # 1 hora
    "auto_renew_credentials": True,
    
    # Adicionar configurações que podem estar faltando
    "download_url_expiry": 3600,  # Tempo de expiração para URLs de download
    "upload_url_expiry": 3600,    # Tempo de expiração para URLs de upload
    "multipart_threshold": 1024 * 1024 * 64,  # 64MB para upload multipart
    "max_pool_connections": 10,    # Máximo de conexões simultâneas
}

# Configurações do SDXL
SDXL_CONFIG = {
    "model_path": SDXL_MODEL_PATH,
    "local_path": SDXL_LOCAL_PATH,
    "vae_path": "madebyollin/sdxl-vae-fp16-fix",
    
    # Configurações de geração
    "width": int(os.getenv("SDXL_WIDTH", "1280")),
    "height": int(os.getenv("SDXL_HEIGHT", "720")),
    "num_inference_steps": int(os.getenv("SDXL_STEPS", "25")),
    "guidance_scale": float(os.getenv("SDXL_GUIDANCE_SCALE", "7.5")),
    "negative_prompt": os.getenv("SDXL_NEGATIVE_PROMPT", "low quality, bad anatomy, worst quality"),
    "batch_size": int(os.getenv("SDXL_BATCH_SIZE", "8")),  # Sem limite máximo
    
    # Otimizações
    "use_fp16": True,
    "enable_vae_tiling": True,
    "torch_compile": True
}

# Configurações do Fish Speech
FISH_SPEECH_CONFIG = {
    "model_path": MODELS_DIR / "fish_speech",
    "voice_dir": MODELS_DIR / "fish_speech" / "voices",
    "custom_voice_dir": MODELS_DIR / "fish_speech" / "custom_voices",
    
    # Configurações de modelo
    "version": "1.4",
    "sample_rate": 22050,
    "hop_length": 256,
    "batch_size": int(os.getenv("FISH_BATCH_SIZE", "4")),
    
    # Otimizações
    "use_compile": True,
    "use_half": True,
    "use_flash_attn": True,
    
    # Configurações de geração
    "max_text_length": int(os.getenv("FISH_MAX_TEXT", "2000")),
    "temperature": float(os.getenv("FISH_TEMP", "0.8")),
    "top_p": float(os.getenv("FISH_TOP_P", "0.9")),
    
    # Idiomas suportados
    "supported_languages": [
        "en-US", "zh-CN", "de-DE", "ja-JP",
        "fr-FR", "es-ES", "ko-KR", "ar-SA",
        "pt-BR", "it-IT", "ru-RU", "hi-IN"
    ],
    
    # Lista de vozes disponíveis
    "available_voices": [
        "male_1", "male_2", "female_1", "female_2",
        "child_1", "elder_1", "neutral_1"
    ],
}

# Configurações do Celery
CELERY_CONFIG = {
    "broker_url": os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    "result_backend": os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
    "task_serializer": "json",
    "result_serializer": "json",
    "accept_content": ["json"],
    "enable_utc": True,
    "task_track_started": True,
    "worker_prefetch_multiplier": 1,
    "task_time_limit": 3600,
    "task_soft_time_limit": 3300
}

# Lista de diretórios necessários
DIRECTORIES_TO_CREATE = [
    MODELS_DIR,
    TEMP_DIR,
    VIDEO_TEMP_DIR,
    SDXL_LOCAL_PATH,
    FISH_SPEECH_CONFIG["model_path"],
    FISH_SPEECH_CONFIG["voice_dir"],
    FISH_SPEECH_CONFIG["custom_voice_dir"]
]

# Criar diretórios
for directory in DIRECTORIES_TO_CREATE:
    directory.mkdir(parents=True, exist_ok=True)

# Log inicial
logger.info(f"Iniciando aplicação {API_TITLE} v{API_VERSION}")
logger.info(f"Modo DEBUG: {DEBUG}")
logger.info(f"Device: {'CUDA' if torch.cuda.is_available() else 'CPU'}")

MODELS_CONFIG = {
    "fish_speech_model_path": os.getenv("FISH_SPEECH_MODEL_PATH", ""),
    # ... outras configurações de modelo ...
}
