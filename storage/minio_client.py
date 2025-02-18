import os
from minio import Minio
from minio.error import S3Error
import uuid
from loguru import logger
from config import MINIO_CONFIG
from dotenv import load_dotenv
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential
from functools import lru_cache

load_dotenv()

@lru_cache(maxsize=1)
def get_minio_client():
    """
    Retorna uma instância única do cliente MinIO.
    Usa cache para evitar múltiplas instanciações.
    """
    try:
        client = Minio(
            endpoint=MINIO_CONFIG["endpoint"],
            access_key=MINIO_CONFIG["access_key"],
            secret_key=MINIO_CONFIG["secret_key"],
            secure=MINIO_CONFIG["secure"]
        )
        
        # Testa a conexão
        client.list_buckets()
        logger.info(f"Cliente MinIO conectado a {MINIO_CONFIG['endpoint']}")
        return client
    except Exception as e:
        logger.error(f"Erro ao conectar ao MinIO: {e}")
        raise

def ensure_bucket():
    """Garante que o bucket existe."""
    try:
        client = get_minio_client()
        bucket = MINIO_CONFIG["bucket_name"]
        
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            logger.info(f"Bucket '{bucket}' criado")
        return True
    except Exception as e:
        logger.error(f"Erro com bucket: {e}")
        return False

def build_public_url(object_name: str) -> str:
    """Constrói URL pública para um objeto."""
    base = MINIO_CONFIG["public_url_base"].rstrip("/")
    bucket = MINIO_CONFIG["bucket_name"]
    return f"{base}/{bucket}/{object_name}"

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def upload_file(file_path: str | Path, object_name: str) -> str:
    """Upload de arquivo com retry."""
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
        
        client = get_minio_client()
        client.fput_object(
            bucket_name=MINIO_CONFIG["bucket_name"],
            object_name=object_name,
            file_path=str(file_path)
        )
        
        return build_public_url(object_name)
    except Exception as e:
        logger.error(f"Erro no upload: {e}")
        raise

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def download_file(object_name: str, file_path: str | Path) -> bool:
    """Download de arquivo com retry."""
    try:
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        client = get_minio_client()
        client.fget_object(
            bucket_name=MINIO_CONFIG["bucket_name"],
            object_name=object_name,
            file_path=str(file_path)
        )
        return True
    except Exception as e:
        logger.error(f"Erro no download: {e}")
        return False

def get_presigned_url(object_name: str, expires_in: int = 3600):
    """
    Gera um link pré-assinado para acessar um arquivo no MinIO.

    :param object_name: Nome do arquivo no MinIO
    :param expires_in: Tempo de expiração do link em segundos (padrão: 1 hora)
    :return: URL pré-assinada para download do arquivo
    """
    try:
        url = get_minio_client().presigned_get_object(
            MINIO_CONFIG["bucket_name"], 
            object_name, 
            expires=expires_in
        )
        return url
    except S3Error as e:
        logger.error(f"Erro ao gerar URL pré-assinada: {str(e)}")
        return None

def list_files():
    """
    Lista todos os arquivos armazenados no MinIO.

    :return: Lista de arquivos no bucket
    """
    try:
        objects = get_minio_client().list_objects(MINIO_CONFIG["bucket_name"])
        return [obj.object_name for obj in objects]
    except S3Error as e:
        logger.error(f"Erro ao listar arquivos: {str(e)}")
        return []

def delete_file(object_name: str):
    """
    Deleta um arquivo do MinIO.

    :param object_name: Nome do arquivo no MinIO
    :return: True se o arquivo foi deletado, False caso contrário
    """
    try:
        get_minio_client().remove_object(MINIO_CONFIG["bucket_name"], object_name)
        logger.info(f"Arquivo {object_name} deletado com sucesso.")
        return True
    except S3Error as e:
        logger.error(f"Erro ao deletar arquivo: {str(e)}")
        return False

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def check_minio_connection(timeout: int = 5) -> bool:
    """
    Verifica se a conexão com o MinIO está funcionando.
    
    Args:
        timeout: Tempo máximo de espera em segundos
        
    Returns:
        bool: True se a conexão está ok, False caso contrário
    """
    try:
        get_minio_client().list_buckets()
        logger.info("Conexão com MinIO estabelecida com sucesso")
        return True
    except Exception as e:
        logger.error(f"Erro ao verificar conexão com MinIO: {str(e)}")
        return False

# Inicialização - Tenta garantir que o bucket existe
if not ensure_bucket():
    logger.warning("Não foi possível garantir a existência do bucket")
