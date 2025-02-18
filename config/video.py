"""
Configurações para processamento de vídeo usando Pydantic.

Este módulo define os parâmetros necessários para:
- Geração de vídeos
- Configurações de codecs
- Parâmetros de renderização
"""

from typing import Dict, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

from .base import base_settings

class VideoSettings(BaseSettings):
    """Configurações de processamento de vídeo."""
    
    # Diretórios
    temp_dir: str = str(base_settings.TEMP_DIR / "video")
    output_dir: str = str(base_settings.MODELS_DIR / "video/output")
    assets_dir: str = str(base_settings.MODELS_DIR / "video/assets")
    
    # Configurações de vídeo
    width: int = 1280
    height: int = 720
    fps: int = 30
    bitrate: str = "4M"
    
    # Configurações de codecs
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    pixel_format: str = "yuv420p"
    
    # Configurações de qualidade
    crf: int = 23  # Constant Rate Factor (18-28 é bom)
    preset: str = "medium"  # ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow
    
    # Configurações de áudio
    audio_bitrate: str = "192k"
    audio_sample_rate: int = 44100
    
    # Configurações de transições
    transition_duration: float = 0.5  # segundos
    default_transition: str = "fade"
    available_transitions: List[str] = [
        "fade",
        "wipe",
        "dissolve",
        "slide",
        "zoom"
    ]
    
    # Configurações de efeitos
    effects_enabled: bool = True
    max_effects_per_scene: int = 3
    available_effects: List[str] = [
        "blur",
        "brightness",
        "contrast",
        "saturation",
        "speed"
    ]
    
    # Configurações de renderização
    max_scenes: int = 50
    max_duration: int = 300  # segundos
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    
    # Configurações de threads
    threads: int = 4
    
    model_config = SettingsConfigDict(
        env_file=".env.video",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    def validate_paths(self) -> None:
        """Valida e cria diretórios necessários."""
        paths = [
            self.temp_dir,
            self.output_dir,
            self.assets_dir
        ]
        for path in paths:
            Path(path).mkdir(parents=True, exist_ok=True)

# Instância global das configurações
video_settings = VideoSettings()
video_settings.validate_paths() 