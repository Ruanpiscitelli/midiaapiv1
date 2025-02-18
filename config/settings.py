"""
Configurações globais da aplicação

Este módulo importa e unifica as configurações de cache e MinIO, além de definir configurações globais (como hf_token, api_key e secret_key) que não possuem prefixo. 
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from config.cache import CacheSettings
from config.minio import MinioSettings

class Settings(BaseSettings):
    # Variáveis globais sem prefixo
    hf_token: str
    api_key: str
    secret_key: str

    # Configurações específicas
    cache: CacheSettings = CacheSettings()
    minio: MinioSettings = MinioSettings()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    class Config:
        env_prefix = ""  # Sem prefixo para as variáveis globais

settings = Settings() 