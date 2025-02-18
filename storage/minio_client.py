import os
from minio import Minio
from minio.error import S3Error
import uuid
from loguru import logger
from config import MINIO_CONFIG
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# Usar configurações do config.py
try:
    minio_client = Minio(
        endpoint=MINIO_CONFIG["endpoint"],  # Apenas host:porta
        access_key=MINIO_CONFIG["access_key"],
        secret_key=MINIO_CONFIG["secret_key"],
        secure=MINIO_CONFIG["secure"],
        region='auto'
    )
    logger.info(f"Cliente MinIO inicializado com endpoint: {MINIO_CONFIG['endpoint']}")
except Exception as e:
    logger.error(f"Erro ao inicializar cliente MinIO: {str(e)}")
    raise

def ensure_bucket_exists():
    """Verifica se o bucket existe e cria se necessário."""
    try:
        if not minio_client.bucket_exists(MINIO_CONFIG["bucket_name"]):
            minio_client.make_bucket(MINIO_CONFIG["bucket_name"])
            logger.info(f"Bucket {MINIO_CONFIG['bucket_name']} criado com sucesso")
    except Exception as e:
        logger.error(f"Erro ao verificar/criar bucket: {str(e)}")

def upload_file(file_path: str | Path, object_name: str) -> str:
    """
    Faz upload de um arquivo para o MinIO.
    
    Args:
        file_path (str | Path): Caminho do arquivo local
        object_name (str): Nome do objeto no MinIO
        
    Returns:
        str: URL do arquivo no MinIO
    """
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
            
        minio_client.fput_object(
            bucket_name=MINIO_CONFIG["bucket_name"],
            object_name=object_name,
            file_path=str(file_path)  # MinIO espera string
        )
        
        # Construindo a URL pública com o path da API
        protocol = "https" if MINIO_CONFIG["api_secure"] else "http"
        api_path = MINIO_CONFIG["api_path"].rstrip("/")  # Remove trailing slash
        return f"{protocol}://{MINIO_CONFIG['api_host']}{api_path}/{MINIO_CONFIG['bucket_name']}/{object_name}"
        
    except Exception as e:
        logger.error(f"Erro no upload do arquivo: {str(e)}")
        raise

def download_file(object_name: str, file_path: str | Path) -> bool:
    """
    Faz download de um arquivo do MinIO.
    
    Args:
        object_name (str): Nome do objeto no MinIO
        file_path (str | Path): Caminho onde salvar o arquivo
        
    Returns:
        bool: True se sucesso, False se falha
    """
    try:
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        minio_client.fget_object(
            bucket_name=MINIO_CONFIG["bucket_name"],
            object_name=object_name,
            file_path=str(file_path)
        )
        return True
    except Exception as e:
        logger.error(f"Erro no download do arquivo: {str(e)}")
        return False

def get_presigned_url(object_name: str, expires_in: int = 3600):
    """
    Gera um link pré-assinado para acessar um arquivo no MinIO.

    :param object_name: Nome do arquivo no MinIO
    :param expires_in: Tempo de expiração do link em segundos (padrão: 1 hora)
    :return: URL pré-assinada para download do arquivo
    """
    try:
        url = minio_client.presigned_get_object(
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
        objects = minio_client.list_objects(MINIO_CONFIG["bucket_name"])
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
        minio_client.remove_object(MINIO_CONFIG["bucket_name"], object_name)
        logger.info(f"Arquivo {object_name} deletado com sucesso.")
        return True
    except S3Error as e:
        logger.error(f"Erro ao deletar arquivo: {str(e)}")
        return False

def check_minio_connection() -> bool:
    """
    Verifica se a conexão com o MinIO está funcionando.
    
    Returns:
        bool: True se a conexão está ok, False caso contrário
    """
    try:
        # Tenta listar buckets para verificar a conexão
        minio_client.list_buckets()
        return True
    except Exception as e:
        logger.error(f"Erro ao verificar conexão com MinIO: {str(e)}")
        return False

# Verifica se o bucket existe ao importar o módulo
ensure_bucket_exists()
