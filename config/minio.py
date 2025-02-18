"""
Configurações para o MinIO utilizando o Pydantic.

Esta classe define os parâmetros necessários para conectar ao MinIO.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict

class MinioSettings(BaseSettings):
    """Configurações do MinIO."""
    endpoint: str = "minio.ruanpiscitelli.com"
    access_key: str = "ts4Xv4Oa01o9HyfujRnH"
    secret_key: str = "BAAp2IWeyR6gVREoxeZMWVbmQM9B7VbuC4U3YHpN"
    secure: bool = True
    bucket: str = "midiaapiv1"
    
    model_config = SettingsConfigDict(
        env_file=".env.minio",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="MINIO_"
    ) 