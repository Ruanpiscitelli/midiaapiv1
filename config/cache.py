"""
Configurações de cache e rate limiting usando Pydantic.
"""

from typing import Dict
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class CacheSettings(BaseSettings):
    """Configurações de cache."""
    REDIS_URL: str = "redis://localhost:6379/1"
    CACHE_PREFIX: str = "midia_api_v1"
    TTL: int = 3600
    MAX_SIZE: int = 1024 * 1024 * 1024  # 1GB
    
    # Tempos específicos de cache
    CACHE_TIMES: Dict[str, int] = {
        "status": 30,      # 30 segundos
        "voices": 3600,    # 1 hora
        "health": 60,      # 1 minuto
        "templates": 3600  # 1 hora
    }
    
    # Configurações de compressão
    COMPRESSION_ENABLED: bool = True
    COMPRESSION_LEVEL: int = 6
    
    # Configurações de fallback
    FALLBACK_ENABLED: bool = True
    FALLBACK_TIMEOUT: int = 5
    
    model_config = SettingsConfigDict(
        env_file=".env.cache",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    def get_config(self) -> dict:
        """Retorna configuração formatada para cache."""
        return {
            "REDIS_URL": self.REDIS_URL,
            "CACHE_PREFIX": self.CACHE_PREFIX,
            "TTL": self.TTL,
            "MAX_SIZE": self.MAX_SIZE,
            "CACHE_TIMES": self.CACHE_TIMES,
            "COMPRESSION": {
                "enabled": self.COMPRESSION_ENABLED,
                "level": self.COMPRESSION_LEVEL
            },
            "FALLBACK": {
                "enabled": self.FALLBACK_ENABLED,
                "timeout": self.FALLBACK_TIMEOUT
            }
        }

class RateLimitSettings(BaseSettings):
    """Configurações de rate limiting."""
    ENABLED: bool = True
    DEFAULT_LIMIT: str = "100/minute"
    STORAGE_URL: str = "redis://localhost:6379/2"
    
    # Limites específicos
    LIMITS: Dict[str, str] = {
        # Limites para geração de conteúdo
        "generate_video": "10/minute",
        "generate_image": "20/minute",
        "generate_tts": "30/minute",
        "clone_voice": "5/minute",
        
        # Limites para consultas
        "status": "100/minute",
        "voices": "50/minute",
        "health": "100/minute",
        
        # Limites para resultados
        "get_result": "100/minute",
        "download": "50/minute"
    }
    
    model_config = SettingsConfigDict(
        env_file=".env.rate_limit",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    def get_config(self) -> dict:
        """Retorna configuração formatada para rate limiting."""
        return {
            "enabled": self.ENABLED,
            "default_limit": self.DEFAULT_LIMIT,
            "storage_url": self.STORAGE_URL,
            "limits": self.LIMITS,
            # Re-exporta limites individuais para acesso direto
            **self.LIMITS
        }

# Instâncias globais
cache_settings = CacheSettings()
rate_limit_settings = RateLimitSettings() 