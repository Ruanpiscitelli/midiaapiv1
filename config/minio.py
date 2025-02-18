"""
Configurações para o MinIO utilizando o Pydantic.

Esta classe define os parâmetros necessários para conectar ao MinIO, utilizando a validação do Pydantic com prefixo de ambiente 'MINIO_'.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict

class MinioSettings(BaseSettings):
    """Configurações do MinIO."""
    url: str = "https://minio.ruanpiscitelli.com/"
    access_key: str = "ts4Xv4Oa01o9HyfujRnH"
    secret_key: str = "BAAp2IWeyR6gVREoxeZMWVbmQM9B7VbuC4U3YHpN"
    api: str = "s3v4"
    path: str = "auto"
    
    model_config = SettingsConfigDict(
        env_file=".env.minio",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    class Config:
        env_prefix = "MINIO_" 