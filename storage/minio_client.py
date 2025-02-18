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

def get_presigned_url(object_name: str, expires_in: int = 3600) -> Optional[str]:
    """
    Gera um link pré-assinado para acessar um arquivo no MinIO.

    Args:
        object_name: Nome do arquivo no MinIO
        expires_in: Tempo de expiração do link em segundos (padrão: 1 hora)

    Returns:
        str | None: URL pré-assinada ou None em caso de erro
    """
    try:
        client = get_minio_client()
        if not client:
            raise RuntimeError("Cliente MinIO não disponível")
            
        url = client.presigned_get_object(
            bucket_name=MINIO_CONFIG["bucket_name"],
            object_name=object_name,
            expires=expires_in
        )
        return url
        
    except Exception as e:
        logger.error(f"Erro ao gerar URL pré-assinada: {str(e)}")
        return None

@retry(
    stop=stop_after_attempt(MINIO_CONFIG["max_retries"]),
    wait=wait_exponential(multiplier=MINIO_CONFIG["retry_delay"], min=1, max=10)
)
def download_file(object_name: str, dest_path: str | Path) -> bool:
    """
    Download de arquivo do MinIO.
    
    Args:
        object_name: Nome do arquivo no MinIO
        dest_path: Caminho local para salvar o arquivo
        
    Returns:
        bool: True se o download foi bem sucedido, False caso contrário
    """
    try:
        client = get_minio_client()
        if not client:
            raise RuntimeError("Cliente MinIO não disponível")
            
        dest_path = Path(dest_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        client.fget_object(
            bucket_name=MINIO_CONFIG["bucket_name"],
            object_name=object_name,
            file_path=str(dest_path)
        )
        return True
        
    except Exception as e:
        logger.error(f"Erro no download: {e}")
        if "token expired" in str(e).lower():
            minio_credentials.last_update = 0
        return False

@retry(
    stop=stop_after_attempt(MINIO_CONFIG["max_retries"]),
    wait=wait_exponential(multiplier=MINIO_CONFIG["retry_delay"], min=1, max=10)
)
def delete_file(object_name: str) -> bool:
    """
    Remove um arquivo do MinIO.
    
    Args:
        object_name: Nome do arquivo no MinIO
        
    Returns:
        bool: True se o arquivo foi deletado com sucesso, False caso contrário
    """
    try:
        client = get_minio_client()
        if not client:
            raise RuntimeError("Cliente MinIO não disponível")
            
        # Verifica se o objeto existe antes de tentar deletar
        try:
            client.stat_object(MINIO_CONFIG["bucket_name"], object_name)
        except Exception:
            logger.warning(f"Arquivo {object_name} não encontrado")
            return False
            
        # Remove o objeto
        client.remove_object(
            bucket_name=MINIO_CONFIG["bucket_name"],
            object_name=object_name
        )
        
        logger.info(f"Arquivo {object_name} deletado com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao deletar arquivo: {e}")
        if "token expired" in str(e).lower():
            minio_credentials.last_update = 0
        return False

def check_minio_connection(timeout: int = 5) -> bool:
    """
    Verifica se a conexão com o MinIO está funcionando.
    
    Args:
        timeout: Tempo máximo de espera em segundos
        
    Returns:
        bool: True se a conexão está ok, False caso contrário
    """
    try:
        client = get_minio_client()
        if not client:
            return False
            
        # Configura timeout para a operação
        original_timeout = client._http.timeout
        client._http.timeout = timeout
        
        try:
            # Tenta listar buckets com timeout
            client.list_buckets()
            return True
        finally:
            # Restaura timeout original
            client._http.timeout = original_timeout
            
    except Exception as e:
        logger.error(f"Erro ao verificar conexão com MinIO: {str(e)}")
        return False

def validate_minio_config():
    """
    Valida se todas as configurações necessárias do MinIO estão presentes.
    
    Returns:
        bool: True se todas as configurações estão presentes
    """
    required_keys = ["max_retries", "retry_delay", "bucket_name"]
    
    for key in required_keys:
        if key not in MINIO_CONFIG:
            logger.error(f"Configuração ausente no MINIO_CONFIG: {key}")
            return False
            
    return True

@retry(
    stop=stop_after_attempt(MINIO_CONFIG.get("max_retries", 3)),  # valor padrão se não definido
    wait=wait_exponential(multiplier=MINIO_CONFIG.get("retry_delay", 1), min=1, max=10)
)
def list_files(prefix: str = "", recursive: bool = True) -> list[str]:
    """
    Lista arquivos no bucket do MinIO.
    
    Args:
        prefix: Prefixo para filtrar arquivos (ex: 'images/', 'videos/')
        recursive: Se deve listar arquivos em subdiretórios
        
    Returns:
        list[str]: Lista de nomes dos arquivos encontrados
    """
    if not validate_minio_config():
        logger.error("Configurações do MinIO inválidas")
        return []
        
    try:
        client = get_minio_client()
        if not client:
            raise RuntimeError("Cliente MinIO não disponível")
            
        # Lista objetos com paginação
        objects = []
        for obj in client.list_objects(
            bucket_name=MINIO_CONFIG["bucket_name"],
            prefix=prefix,
            recursive=recursive
        ):
            objects.append(obj.object_name)
            
        logger.debug(f"Listados {len(objects)} arquivos com prefixo '{prefix}'")
        return objects
        
    except Exception as e:
        logger.error(f"Erro ao listar arquivos: {e}")
        if "token expired" in str(e).lower():
            minio_credentials.last_update = 0
        return []

# Validação inicial das configurações
if not validate_minio_config():
    logger.warning("Configurações do MinIO incompletas ou inválidas")

# Inicialização
if not ensure_bucket():
    logger.warning("Não foi possível garantir a existência do bucket")
