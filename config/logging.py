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
    format: str = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
    datefmt: str = "%Y-%m-%d %H:%M:%S.%f"
    
    # Configurações de arquivo
    file_format: str = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
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
        Retorna configuração formatada para uso com logging.config.dictConfig.
        """
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": self.format,
                    "datefmt": self.datefmt
                },
                "file": {
                    "format": self.file_format,
                    "datefmt": self.datefmt
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "stream": "ext://sys.stdout",
                    "level": self.default_level
                },
                "file": {
                    "class": "logging.handlers.TimedRotatingFileHandler",
                    "formatter": "file",
                    "filename": f"{self.log_dir}/app.log",
                    "when": "midnight",
                    "interval": 1,
                    "backupCount": 30,
                    "encoding": "utf-8",
                    "level": self.default_level
                }
            },
            "loggers": {
                # Configurações específicas por módulo
                **{
                    logger: {
                        "level": level,
                        "handlers": ["console", "file"],
                        "propagate": False
                    }
                    for logger, level in self.module_levels.items()
                },
                # Logger raiz
                "": {
                    "level": self.default_level,
                    "handlers": ["console", "file"],
                    "propagate": True
                }
            }
        }

# Instância global das configurações
logging_settings = LoggingSettings() 