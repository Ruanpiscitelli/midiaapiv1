"""
Configurações globais otimizadas para máxima performance.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import logging.config
import torch

# Carrega variáveis de ambiente
load_dotenv()

# Diretórios base
BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"
TEMP_DIR = BASE_DIR / "temp"

# Caminhos específicos
SDXL_LOCAL_PATH = MODELS_DIR / "sdxl"
VIDEO_TEMP_DIR = TEMP_DIR / "video"
FISH_SPEECH_MODEL_PATH = MODELS_DIR / "fish_speech"

# Configurações da API
API_VERSION = "2.0"
API_TITLE = "Gerador de Vídeos com IA"
API_KEY = os.getenv("API_KEY", "minha-chave-api")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Otimizações de GPU
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
NUM_GPUS = torch.cuda.device_count() if torch.cuda.is_available() else 0
CUDA_VISIBLE_DEVICES = os.getenv("CUDA_VISIBLE_DEVICES", "all")

# Configurações do SDXL otimizadas
SDXL_CONFIG = {
    "model_path": os.getenv("SDXL_MODEL_PATH", "stabilityai/stable-diffusion-xl-base-1.0"),
    "local_path": SDXL_LOCAL_PATH,
    "vae_path": "madebyollin/sdxl-vae-fp16-fix",
    
    # Removidas limitações de resolução
    "width": int(os.getenv("SDXL_WIDTH", "1280")),
    "height": int(os.getenv("SDXL_HEIGHT", "720")),
    
    # Parâmetros de geração
    "num_inference_steps": int(os.getenv("SDXL_STEPS", "25")),
    "guidance_scale": float(os.getenv("SDXL_GUIDANCE_SCALE", "7.5")),
    "negative_prompt": os.getenv("SDXL_NEGATIVE_PROMPT", "low quality, bad anatomy, worst quality"),
    
    # Otimizações de performance
    "batch_size": int(os.getenv("SDXL_BATCH_SIZE", "8")),  # Sem limite máximo
    "use_fp16": True,  # Usa precisão reduzida para economia de VRAM
    "enable_vae_tiling": True,  # Habilita tiling do VAE para imagens grandes
    "enable_sequential_cpu_offload": False,  # Mantém na GPU para máxima performance
    "enable_attention_slicing": False,  # Desabilitado para máxima performance
    "enable_model_cpu_offload": False,  # Mantém na GPU
    "torch_compile": True,  # Usa torch.compile para otimização
    "use_deterministic": False,  # Desabilita para máxima performance
    
    # Multi-GPU
    "enable_model_parallel": NUM_GPUS > 1,
    "gpu_ids": list(range(NUM_GPUS)),
    
    # Cache e otimizações de memória
    "model_cpu_offload": False,
    "attention_slicing": None,
    "vae_slicing": False,
    
    # Timeouts e retries (aumentados)
    "max_retries": int(os.getenv("SDXL_MAX_RETRIES", "5")),
    "timeout": int(os.getenv("SDXL_TIMEOUT", "600"))  # 10 minutos
}

# Configurações do Fish Speech baseadas na documentação oficial.
FISH_SPEECH_CONFIG = {
    "model_path": MODELS_DIR / "fish_speech",
    "voice_dir": MODELS_DIR / "fish_speech" / "voices",
    "custom_voice_dir": MODELS_DIR / "fish_speech" / "custom_voices",
    
    # Configurações de modelo
    "version": "1.4",  # Versão mais estável
    "sample_rate": 22050,
    "hop_length": 256,
    "batch_size": 1,
    
    # Otimizações de performance
    "use_compile": True,  # Usa torch.compile para acelerar
    "use_half": True,    # Usa FP16 para GPUs que suportam
    "use_flash_attn": True,  # Usa Flash Attention se disponível
    "use_checkpointing": True,  # Usa gradient checkpointing para economia de memória
    
    # Configurações de geração
    "max_text_length": 1000,
    "temperature": 0.8,
    "top_p": 0.9,
    
    # Idiomas suportados (baseado na documentação)
    "supported_languages": [
        "en-US",  # ~300k horas
        "zh-CN",  # ~300k horas
        "de-DE",  # ~20k horas
        "ja-JP",  # ~20k horas
        "fr-FR",  # ~20k horas
        "es-ES",  # ~20k horas
        "ko-KR",  # ~20k horas
        "ar-SA",  # ~20k horas
        "pt-BR"   # Suporte adicionado
    ]
}

# Configurações de vídeo otimizadas
VIDEO_CONFIG = {
    "default_resolution": {
        "width": int(os.getenv("VIDEO_WIDTH", "1920")),
        "height": int(os.getenv("VIDEO_HEIGHT", "1080"))
    },
    "fps": int(os.getenv("VIDEO_FPS", "30")),
    "codec": os.getenv("VIDEO_CODEC", "h264_nvenc" if torch.cuda.is_available() else "libx264"),
    "audio_codec": "aac",
    "temp_dir": VIDEO_TEMP_DIR,
    "output_format": "mp4",
    "bitrate": os.getenv("VIDEO_BITRATE", "8M"),  # Aumentado para melhor qualidade
    "gpu_acceleration": torch.cuda.is_available(),
    "threads": os.cpu_count()  # Usa todos os cores disponíveis
}

# Configurações do Celery otimizadas
CELERY_CONFIG = {
    "broker_url": os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    "result_backend": os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
    "task_serializer": "json",
    "result_serializer": "json",
    "accept_content": ["json"],
    "enable_utc": True,
    "task_track_started": True,
    "worker_prefetch_multiplier": 4,  # Aumentado para melhor throughput
    "task_time_limit": 7200,  # 2 horas
    "task_soft_time_limit": 6900,
    "worker_max_tasks_per_child": None,  # Sem limite
    "worker_max_memory_per_child": None  # Sem limite de memória
}

# Configurações do MinIO (mantidas as mesmas)
MINIO_CONFIG = {
    "endpoint": os.getenv("MINIO_ENDPOINT", "minio.ruanpiscitelli.com").split("://")[-1],
    "access_key": os.getenv("MINIO_ACCESS_KEY", "ts4Xv4Oa01o9HyfujRnH"),
    "secret_key": os.getenv("MINIO_SECRET_KEY", "BAAp2IWeyR6gVREoxeZMWVbmQM9B7VbuC4U3YHpN"),
    "secure": True,
    "bucket_name": os.getenv("MINIO_BUCKET", "media-bucket"),
    "public_url_base": "https://minio.ruanpiscitelli.com/api/v1"
}

# Diretórios necessários
DIRECTORIES_TO_CREATE = [
    MODELS_DIR,
    TEMP_DIR,
    VIDEO_TEMP_DIR,
    SDXL_LOCAL_PATH,
    FISH_SPEECH_CONFIG["model_path"],
    FISH_SPEECH_CONFIG["voice_dir"],
    FISH_SPEECH_CONFIG["custom_voice_dir"]
]

# Criação de diretórios
for directory in DIRECTORIES_TO_CREATE:
    directory.mkdir(parents=True, exist_ok=True)

# Configuração de logging
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# Log de configurações
logger.info(f"Iniciando {API_TITLE} v{API_VERSION}")
logger.info(f"Modo DEBUG: {DEBUG}")
logger.info(f"Device: {DEVICE} ({NUM_GPUS} GPUs disponíveis)")
logger.info(f"Batch Size SDXL: {SDXL_CONFIG['batch_size']}")
logger.info(f"Otimizações CUDA: {'Ativadas' if torch.cuda.is_available() else 'Desativadas'}")
