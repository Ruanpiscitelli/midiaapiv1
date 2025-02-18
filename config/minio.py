"""
Configurações para o MinIO utilizando o Pydantic.

Esta classe define os parâmetros necessários para conectar ao MinIO.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict

class MinioSettings(BaseSettings):
    """Configurações do MinIO."""
    # Configurações de conexão
    endpoint: str = "minio.ruanpiscitelli.com"
    access_key: str = "ts4Xv4Oa01o9HyfujRnH"
    secret_key: str = "BAAp2IWeyR6gVREoxeZMWVbmQM9B7VbuC4U3YHpN"
    secure: bool = True
    
    # Configurações de bucket
    bucket_name: str = "arquivosapi"
    bucket_region: str = "us-east-1"
    
    # Configurações de retry
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # Configurações de timeout
    connection_timeout: float = 5.0
    read_timeout: float = 10.0
    
    model_config = SettingsConfigDict(
        env_file=".env.minio",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="MINIO_"
    ) 