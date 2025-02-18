"""
Configurações globais do projeto.
Este módulo contém todas as configurações necessárias para o funcionamento da aplicação.

Documentação:
- Todas as configurações são carregadas de variáveis de ambiente ou valores padrão
- Os diretórios são criados automaticamente se não existirem
- As configurações são organizadas por módulo/funcionalidade
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import logging.config
import torch

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Diretórios base
BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"
TEMP_DIR = BASE_DIR / "temp"

# Atualiza caminhos específicos usando Path
SDXL_MODEL_PATH = MODELS_DIR / "sdxl"
FISH_SPEECH_MODEL_PATH = MODELS_DIR / "fish_speech"
VIDEO_TEMP_DIR = TEMP_DIR / "video"

# Configurações da API
API_VERSION = "2.0"
API_TITLE = "Gerador de Vídeos com IA"
API_KEY = os.getenv("API_KEY", "minha-chave-api")  # Chave padrão apenas para desenvolvimento
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Configurações do Stable Diffusion XL
SDXL_MODEL_PATH = "stabilityai/stable-diffusion-xl-base-1.0"  # Usa modelo do HuggingFace
# ou
# SDXL_MODEL_PATH = str(Path(__file__).parent / "models" / "sdxl")  # Para modelo local

# Dispositivo para inferência
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

SDXL_CONFIG = {
    "model_path": SDXL_MODEL_PATH,
    "vae_path": "madebyollin/sdxl-vae-fp16-fix",
    "width": min(int(os.getenv("SDXL_WIDTH", "1280")), 2048),
    "height": min(int(os.getenv("SDXL_HEIGHT", "720")), 2048),
    "num_inference_steps": min(int(os.getenv("SDXL_STEPS", "25")), 150),
    "guidance_scale": float(os.getenv("SDXL_GUIDANCE_SCALE", "7.5")),
    "negative_prompt": os.getenv(
        "SDXL_NEGATIVE_PROMPT",
        "low quality, bad anatomy, worst quality, low resolution"
    ),
    "batch_size": min(int(os.getenv("SDXL_BATCH_SIZE", "4")), 8),
    "max_retries": int(os.getenv("SDXL_MAX_RETRIES", "3")),
    "timeout": int(os.getenv("SDXL_TIMEOUT", "300"))
}

# Configurações do Fish Speech
FISH_SPEECH_CONFIG = {
    "model_path": FISH_SPEECH_MODEL_PATH / "model.pth",
    "available_voices": ["male_1", "female_1"],
    "voice_dir": FISH_SPEECH_MODEL_PATH / "voices",
    "custom_voice_dir": FISH_SPEECH_MODEL_PATH / "custom_voices",
    "supported_languages": ["pt-BR", "en-US"],
    "sample_rate": 44100,
    "real_time_factor": 5  # ~5 segundos de processamento por segundo de áudio
}

# Configurações do MinIO
MINIO_CONFIG = {
    "endpoint": os.getenv("MINIO_ENDPOINT", "localhost:9000"),
    "access_key": os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
    "secret_key": os.getenv("MINIO_SECRET_KEY", "minioadmin"),
    "secure": os.getenv("MINIO_SECURE", "False").lower() == "true",
    "bucket_name": os.getenv("MINIO_BUCKET", "media-bucket"),
    "presigned_url_expiry": 3600  # URLs pré-assinadas expiram em 1 hora
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
    "worker_prefetch_multiplier": 1,  # Evita que um worker pegue muitas tasks de GPU
    "task_time_limit": 3600,  # Timeout de 1 hora por tarefa
    "task_soft_time_limit": 3300  # Aviso de timeout 5 minutos antes
}

# Configurações do banco de dados
DATABASE_CONFIG = {
    "url": os.getenv("DATABASE_URL", "sqlite:///./db/logs.db"),
    "connect_args": {"check_same_thread": False},  # Necessário para SQLite
    "echo": DEBUG  # Logs SQL apenas em modo debug
}

# Configurações de vídeo
VIDEO_CONFIG = {
    "default_resolution": {
        "width": 1280,
        "height": 720
    },
    "fps": 30,
    "codec": "libx264",
    "audio_codec": "aac",
    "temp_dir": VIDEO_TEMP_DIR,
    "output_format": "mp4",
    "bitrate": "4M"  # Bitrate padrão para vídeo HD
}

# Configurações de segurança
SECURITY_CONFIG = {
    "algorithm": "HS256",
    "access_token_expire_minutes": 30,
    "refresh_token_expire_days": 7,
    "secret_key": os.getenv("SECRET_KEY", "sua-chave-secreta-aqui")
}

# Configurações de logging
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": "INFO"
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": "app.log",
            "formatter": "default",
            "level": "INFO"
        }
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO"
    }
}

# Lista atualizada de diretórios que precisam ser criados
DIRECTORIES_TO_CREATE = [
    MODELS_DIR,
    TEMP_DIR,
    VIDEO_CONFIG["temp_dir"],
    SDXL_MODEL_PATH,
    FISH_SPEECH_MODEL_PATH,
    FISH_SPEECH_CONFIG["voice_dir"],
    FISH_SPEECH_CONFIG["custom_voice_dir"]
]

# Criar diretórios necessários
for directory in DIRECTORIES_TO_CREATE:
    directory.mkdir(parents=True, exist_ok=True)

# Configurar logging
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# Log inicial
logger.info(f"Iniciando aplicação {API_TITLE} v{API_VERSION}")
logger.info(f"Modo DEBUG: {DEBUG}")

# Validações críticas
if not API_KEY or len(API_KEY) < 32:
    logger.warning("API_KEY não configurada ou muito curta. Use uma chave forte em produção!")

if MINIO_CONFIG["access_key"] == "minioadmin" or MINIO_CONFIG["secret_key"] == "minioadmin":
    logger.warning("Credenciais padrão do MinIO em uso. Altere em produção!")

if SECURITY_CONFIG["secret_key"] == "sua-chave-secreta-aqui":
    logger.warning("Chave secreta padrão em uso. Defina uma chave forte em produção!")

# Configurações de recursos
RESOURCE_LIMITS = {
    "max_concurrent_tasks": int(os.getenv("MAX_CONCURRENT_TASKS", "4")),
    "max_batch_size": int(os.getenv("MAX_BATCH_SIZE", "8")),
    "max_video_duration": int(os.getenv("MAX_VIDEO_DURATION", "300")),  # em segundos
    "max_file_size": int(os.getenv("MAX_FILE_SIZE", "100")) * 1024 * 1024,  # em bytes
}

# Log de configurações críticas
logger.info(f"Resolução SDXL: {SDXL_CONFIG['width']}x{SDXL_CONFIG['height']}")
logger.info(f"Batch size: {SDXL_CONFIG['batch_size']}")
logger.info(f"Limites de recursos configurados: {RESOURCE_LIMITS}")
 