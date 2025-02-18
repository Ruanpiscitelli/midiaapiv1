"""
Configurações dos modelos de IA usando Pydantic.
"""

from typing import Dict, Any, List
from pathlib import Path
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
import os
import torch

from .base import base_settings

class SDXLConfig(BaseModel):
    """Configurações do modelo SDXL."""
    model_path: str = "stabilityai/stable-diffusion-xl-base-1.0"
    local_path: str = str(base_settings.MODELS_DIR / "sdxl")
    vae_path: str = "madebyollin/sdxl-vae-fp16-fix"
    width: int = 1280
    height: int = 720
    num_inference_steps: int = 25
    guidance_scale: float = 7.5
    negative_prompt: str = "low quality, bad anatomy, worst quality"
    batch_size: int = 8
    use_fp16: bool = True
    enable_vae_tiling: bool = True
    torch_compile: bool = True

class FishSpeechConfig(BaseModel):
    """Configurações do modelo Fish Speech."""
    model_path: str = str(base_settings.MODELS_DIR / "fish_speech")
    voice_dir: str = str(base_settings.MODELS_DIR / "fish_speech/voices")
    custom_voice_dir: str = str(base_settings.MODELS_DIR / "fish_speech/custom_voices")
    version: str = "1.4"
    sample_rate: int = 22050
    hop_length: int = 256
    batch_size: int = 4
    use_compile: bool = True
    use_half: bool = True
    use_flash_attn: bool = True
    max_text_length: int = 2000
    temperature: float = 0.8
    top_p: float = 0.9
    supported_languages: List[str] = [
        "en-US", "zh-CN", "de-DE", "ja-JP",
        "fr-FR", "es-ES", "ko-KR", "ar-SA",
        "pt-BR", "it-IT", "ru-RU", "hi-IN"
    ]
    available_voices: List[str] = [
        "male_1", "male_2", "female_1", "female_2",
        "child_1", "elder_1", "neutral_1"
    ]

class StorageConfig(BaseModel):
    """Configurações de armazenamento."""
    storage_type: str = "minio"
    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "minio:9000")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    minio_bucket: str = os.getenv("MINIO_BUCKET", "arquivosapi")
    minio_secure: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"

class SecurityConfig(BaseModel):
    """Configurações de segurança."""
    api_key: str = os.getenv("API_KEY", "seu-token-secreto")
    secret_key: str = os.getenv("SECRET_KEY", "chave-secreta-para-jwt")
    hf_token: str = os.getenv("HF_TOKEN", "")

class ModelsSettings(BaseSettings):
    """Configurações gerais dos modelos."""
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    num_gpus: int = torch.cuda.device_count() if torch.cuda.is_available() else 0
    
    # Configurações específicas
    sdxl: SDXLConfig = SDXLConfig()
    fish_speech: FishSpeechConfig = FishSpeechConfig()
    storage: StorageConfig = StorageConfig()
    security: SecurityConfig = SecurityConfig()
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    def validate_paths(self) -> None:
        """Valida e cria diretórios necessários."""
        paths = [
            self.sdxl.local_path,
            self.fish_speech.model_path,
            self.fish_speech.voice_dir,
            self.fish_speech.custom_voice_dir
        ]
        for path in paths:
            Path(path).mkdir(parents=True, exist_ok=True)

# Instância global das configurações
models_settings = ModelsSettings() 