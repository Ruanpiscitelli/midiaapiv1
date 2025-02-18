import os
from minio import Minio
from minio.error import S3Error
import uuid
from loguru import logger
from config import MINIO_CONFIG
from dotenv import load_dotenv

load_dotenv()

# Configurações do MinIO
MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'minio.ruanpiscitelli.com')
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'ts4Xv4Oa01o9HyfujRnH')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'BAAp2IWeyR6gVREoxeZMWVbmQM9B7VbuC4U3YHpN')
MINIO_BUCKET = os.getenv('MINIO_BUCKET', 'arquivosapi')
MINIO_SECURE = os.getenv('MINIO_SECURE', 'true').lower() == 'true'

# Inicializa o cliente MinIO
minio_client = Minio(
    endpoint=MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE,
    region='auto'  # Adiciona configuração da região
)

def ensure_bucket_exists():
    """Verifica se o bucket existe e cria se necessário."""
    try:
        if not minio_client.bucket_exists(MINIO_BUCKET):
            minio_client.make_bucket(MINIO_BUCKET)
    except Exception as e:
        print(f"Erro ao verificar/criar bucket: {str(e)}")
        # Não levanta exceção, apenas loga o erro

def upload_file(file_path: str, object_name: str) -> str:
    """
    Faz upload de um arquivo para o MinIO.
    
    Args:
        file_path (str): Caminho do arquivo local
        object_name (str): Nome do objeto no MinIO
        
    Returns:
        str: URL do arquivo no MinIO
    """
    try:
        # Faz o upload do arquivo
        minio_client.fput_object(
            bucket_name=MINIO_BUCKET,
            object_name=object_name,
            file_path=file_path
        )
        
        # Retorna a URL do arquivo
        return f"https://{MINIO_ENDPOINT}/{MINIO_BUCKET}/{object_name}"
        
    except Exception as e:
        print(f"Erro no upload do arquivo: {str(e)}")
        raise

def download_file(object_name: str, file_path: str) -> bool:
    """
    Faz download de um arquivo do MinIO.
    
    Args:
        object_name (str): Nome do objeto no MinIO
        file_path (str): Caminho onde salvar o arquivo
        
    Returns:
        bool: True se sucesso, False se falha
    """
    try:
        minio_client.fget_object(
            bucket_name=MINIO_BUCKET,
            object_name=object_name,
            file_path=file_path
        )
        return True
    except Exception as e:
        print(f"Erro no download do arquivo: {str(e)}")
        return False

def get_presigned_url(object_name: str, expires_in: int = 3600):
    """
    Gera um link pré-assinado para acessar um arquivo no MinIO.

    :param object_name: Nome do arquivo no MinIO
    :param expires_in: Tempo de expiração do link em segundos (padrão: 1 hora)
    :return: URL pré-assinada para download do arquivo
    """
    try:
        url = minio_client.presigned_get_object(MINIO_BUCKET, object_name, expires=expires_in)
        return url
    except S3Error as e:
        print(f"Erro ao gerar URL pré-assinada: {str(e)}")
        return None

def list_files():
    """
    Lista todos os arquivos armazenados no MinIO.

    :return: Lista de arquivos no bucket
    """
    try:
        objects = minio_client.list_objects(MINIO_BUCKET)
        return [obj.object_name for obj in objects]
    except S3Error as e:
        print(f"Erro ao listar arquivos: {str(e)}")
        return []

def delete_file(object_name: str):
    """
    Deleta um arquivo do MinIO.

    :param object_name: Nome do arquivo no MinIO
    :return: True se o arquivo foi deletado, False caso contrário
    """
    try:
        minio_client.remove_object(MINIO_BUCKET, object_name)
        print(f"Arquivo {object_name} deletado com sucesso.")
        return True
    except S3Error as e:
        print(f"Erro ao deletar arquivo: {str(e)}")
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
