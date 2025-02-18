"""
Configurações dos modelos de IA usando Pydantic.
"""

from typing import Dict, Any, List, Literal
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

class ModelsSettings(BaseSettings):
    """Configurações gerais dos modelos."""
    # Configurações de Hardware
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    num_gpus: int = torch.cuda.device_count() if torch.cuda.is_available() else 0
    
    # Configurações de Storage
    storage_type: Literal["local", "minio"] = "minio"
    
    # Configurações de Segurança
    hf_token: str = os.getenv("HF_TOKEN", "")
    api_key: str = os.getenv("API_KEY", "seu-token-secreto")
    secret_key: str = os.getenv("SECRET_KEY", "chave-secreta-para-jwt")
    
    # Configurações do MinIO
    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "minio:9000")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    minio_bucket: str = os.getenv("MINIO_BUCKET", "arquivosapi")
    minio_secure: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"
    
    # Configurações dos Modelos
    sdxl: SDXLConfig = SDXLConfig()
    fish_speech: FishSpeechConfig = FishSpeechConfig()
    
    model_config = SettingsConfigDict(
        env_file=".env.models",
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
            
    def get_config(self) -> dict:
        """Retorna configuração formatada para os modelos."""
        return {
            # Hardware e ambiente
            "device": self.device,
            "num_gpus": self.num_gpus,
            "storage_type": self.storage_type,
            
            # Credenciais e tokens
            "hf_token": self.hf_token,
            "api_key": self.api_key,
            "secret_key": self.secret_key,
            
            # MinIO
            "minio": {
                "endpoint": self.minio_endpoint,
                "access_key": self.minio_access_key,
                "secret_key": self.minio_secret_key,
                "bucket": self.minio_bucket,
                "secure": self.minio_secure
            },
            
            # SDXL
            "sdxl": self.get_sdxl_config(),
            
            # Fish Speech
            "fish_speech": self.get_fish_speech_config()
        }
        
    def get_sdxl_config(self) -> dict:
        """Retorna configuração específica do modelo SDXL."""
        return {
            "model_path": self.sdxl.model_path,
            "local_path": self.sdxl.local_path,
            "vae_path": self.sdxl.vae_path,
            "width": self.sdxl.width,
            "height": self.sdxl.height,
            "num_inference_steps": self.sdxl.num_inference_steps,
            "guidance_scale": self.sdxl.guidance_scale,
            "negative_prompt": self.sdxl.negative_prompt,
            "batch_size": self.sdxl.batch_size,
            "use_fp16": self.sdxl.use_fp16,
            "enable_vae_tiling": self.sdxl.enable_vae_tiling,
            "torch_compile": self.sdxl.torch_compile
        }
        
    def get_fish_speech_config(self) -> dict:
        """Retorna configuração específica do modelo Fish Speech."""
        return {
            "model_path": self.fish_speech.model_path,
            "voice_dir": self.fish_speech.voice_dir,
            "custom_voice_dir": self.fish_speech.custom_voice_dir,
            "version": self.fish_speech.version,
            "sample_rate": self.fish_speech.sample_rate,
            "hop_length": self.fish_speech.hop_length,
            "batch_size": self.fish_speech.batch_size,
            "use_compile": self.fish_speech.use_compile,
            "use_half": self.fish_speech.use_half,
            "use_flash_attn": self.fish_speech.use_flash_attn,
            "max_text_length": self.fish_speech.max_text_length,
            "temperature": self.fish_speech.temperature,
            "top_p": self.fish_speech.top_p,
            "supported_languages": self.fish_speech.supported_languages,
            "available_voices": self.fish_speech.available_voices
        }

# Instância global das configurações
models_settings = ModelsSettings() 