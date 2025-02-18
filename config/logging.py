"""
Configurações de logging usando Pydantic.

Este módulo define os parâmetros necessários para:
- Configuração dos logs da aplicação
- Formatação das mensagens
- Rotação de arquivos
- Níveis de log por módulo
"""

from typing import Dict, List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import os

from .base import base_settings

class LoggingSettings(BaseSettings):
    """Configurações de logging."""
    
    # Diretório base para logs
    log_dir: str = str(base_settings.BASE_DIR / "logs")
    
    # Nível de log padrão
    default_level: str = "INFO"
    
    # Formato das mensagens
    format: str = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    
    # Configurações de arquivo
    file_format: str = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}"
    rotation: str = "1 day"
    retention: str = "1 month"
    compression: str = "zip"
    
    # Níveis por módulo
    module_levels: Dict[str, str] = {
        "uvicorn": "INFO",
        "sqlalchemy": "WARNING",
        "celery": "INFO",
        "minio": "INFO",
        "stable_diffusion": "INFO",
        "tts": "INFO",
        "video": "INFO"
    }
    
    # Configurações de diagnóstico
    diagnose: bool = True
    backtrace: bool = True
    
    # Configurações de serialização
    serialize: bool = False
    json_logs: bool = False
    
    # Configurações de colorização
    colorize: bool = True
    
    # Configurações de captura
    capture_warnings: bool = True
    capture_exceptions: bool = True
    
    model_config = SettingsConfigDict(
        env_file=".env.logging",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Cria diretório de logs se não existir
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)
        
    def get_config(self) -> Dict:
        """
        Retorna configuração formatada para uso com loguru.
        """
        return {
            "handlers": [
                # Handler para console
                {
                    "sink": "sys.stdout",
                    "format": self.format,
                    "colorize": self.colorize,
                    "level": self.default_level
                },
                # Handler para arquivo
                {
                    "sink": f"{self.log_dir}/app.log",
                    "format": self.file_format,
                    "rotation": self.rotation,
                    "retention": self.retention,
                    "compression": self.compression,
                    "level": self.default_level,
                    "serialize": self.serialize
                }
            ],
            "levels": [
                {"name": "TRACE", "no": 5, "color": "<cyan>"},
                {"name": "DEBUG", "no": 10, "color": "<blue>"},
                {"name": "INFO", "no": 20, "color": "<green>"},
                {"name": "SUCCESS", "no": 25, "color": "<green>"},
                {"name": "WARNING", "no": 30, "color": "<yellow>"},
                {"name": "ERROR", "no": 40, "color": "<red>"},
                {"name": "CRITICAL", "no": 50, "color": "<RED>"}
            ],
            "extra": {
                "app_name": "MidiaAPI",
                "version": base_settings.API_VERSION,
                "environment": base_settings.ENVIRONMENT
            },
            "activation": [
                *[
                    (logger, level)
                    for logger, level in self.module_levels.items()
                ]
            ],
            "diagnose": self.diagnose,
            "backtrace": self.backtrace,
            "capture_warnings": self.capture_warnings,
            "capture_exceptions": self.capture_exceptions
        }

# Instância global das configurações
logging_settings = LoggingSettings() 