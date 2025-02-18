import os
import time
import requests
from minio import Minio
from minio.error import S3Error
import uuid
from loguru import logger
from config import MINIO_CONFIG
from dotenv import load_dotenv
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential
from functools import lru_cache
from typing import Dict, Optional
import json

load_dotenv()

class MinioCredentials:
    """Gerenciador de credenciais do MinIO."""
    
    def __init__(self):
        self.credentials: Dict = {}
        self.last_update: float = 0
        
    def needs_update(self) -> bool:
        """Verifica se as credenciais precisam ser atualizadas."""
        return (time.time() - self.last_update) > MINIO_CONFIG["credentials_cache_time"]
    
    def update_credentials(self) -> bool:
        """Atualiza as credenciais via API."""
        try:
            response = requests.get(
                MINIO_CONFIG["service_account_url"],
                timeout=MINIO_CONFIG["connection_timeout"]
            )
            response.raise_for_status()
            
            credentials = response.json()
            self.credentials = {
                "access_key": credentials.get("accessKey"),
                "secret_key": credentials.get("secretKey"),
                "session_token": credentials.get("sessionToken")
            }
            
            self.last_update = time.time()
            logger.info("Credenciais do MinIO atualizadas com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao atualizar credenciais: {e}")
            return False

# Instância global das credenciais
minio_credentials = MinioCredentials()

@lru_cache(maxsize=1)
def get_minio_client() -> Optional[Minio]:
    """
    Retorna cliente MinIO com credenciais atualizadas.
    """
    try:
        # Atualiza credenciais se necessário
        if minio_credentials.needs_update():
            if not minio_credentials.update_credentials():
                raise RuntimeError("Falha ao atualizar credenciais")
        
        # Cria cliente com as credenciais atuais
        client = Minio(
            endpoint=MINIO_CONFIG["endpoint"],
            access_key=minio_credentials.credentials["access_key"],
            secret_key=minio_credentials.credentials["secret_key"],
            session_token=minio_credentials.credentials["session_token"],
            secure=MINIO_CONFIG["secure"],
            region=MINIO_CONFIG["region"]
        )
        
        # Testa conexão
        client.list_buckets()
        return client
        
    except Exception as e:
        logger.error(f"Erro ao criar cliente MinIO: {e}")
        return None

def ensure_bucket() -> bool:
    """Garante que o bucket existe com as configurações corretas."""
    try:
        client = get_minio_client()
        if not client:
            return False
            
        bucket = MINIO_CONFIG["bucket_name"]
        
        if not client.bucket_exists(bucket):
            client.make_bucket(
                bucket,
                location=MINIO_CONFIG["bucket_region"]
            )
            logger.info(f"Bucket '{bucket}' criado")
            
        return True
        
    except Exception as e:
        logger.error(f"Erro com bucket: {e}")
        return False

@retry(
    stop=stop_after_attempt(MINIO_CONFIG["max_retries"]),
    wait=wait_exponential(
        multiplier=MINIO_CONFIG["retry_delay"],
        min=1,
        max=10
    )
)
def upload_file(file_path: str | Path, object_name: str) -> Optional[str]:
    """Upload de arquivo com retry e renovação automática de credenciais."""
    try:
        client = get_minio_client()
        if not client:
            raise RuntimeError("Cliente MinIO não disponível")
            
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
        
        # Upload com metadata
        client.fput_object(
            bucket_name=MINIO_CONFIG["bucket_name"],
            object_name=object_name,
            file_path=str(file_path),
            metadata={
                "uploaded_at": str(time.time()),
                "original_name": file_path.name
            }
        )
        
        return build_public_url(object_name)
        
    except Exception as e:
        logger.error(f"Erro no upload: {e}")
        if "token expired" in str(e).lower():
            # Força atualização de credenciais
            minio_credentials.last_update = 0
        return None

def build_public_url(object_name: str) -> str:
    """Constrói URL pública para um objeto."""
    base = MINIO_CONFIG["public_url_base"].rstrip("/")
    bucket = MINIO_CONFIG["bucket_name"]
    return f"{base}/{bucket}/{object_name}"

# Inicialização
if not ensure_bucket():
    logger.warning("Não foi possível garantir a existência do bucket")
