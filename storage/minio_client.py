import os
from minio import Minio
from minio.error import S3Error
import uuid
from loguru import logger
from config import MINIO_CONFIG

# Configuração do MinIO (pega as credenciais do ambiente)
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "password")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "media")

# Inicializa o cliente MinIO
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False  # Defina como True se estiver usando HTTPS
)

# Certifica-se de que o bucket existe
def ensure_bucket_exists():
    """ Verifica e cria o bucket caso ele não exista. """
    found = minio_client.bucket_exists(MINIO_BUCKET)
    if not found:
        minio_client.make_bucket(MINIO_BUCKET)
        print(f"Bucket '{MINIO_BUCKET}' criado com sucesso.")

ensure_bucket_exists()

def upload_file(file_path: str, object_name: str):
    """
    Faz upload de um arquivo para o MinIO.

    :param file_path: Caminho do arquivo local
    :param object_name: Nome do arquivo no MinIO (ex: "images/meuarquivo.png")
    :return: URL do arquivo no MinIO
    """
    try:
        minio_client.fput_object(MINIO_BUCKET, object_name, file_path)
        print(f"Arquivo {object_name} enviado para o MinIO com sucesso.")
        return f"{MINIO_ENDPOINT}/{MINIO_BUCKET}/{object_name}"
    except S3Error as e:
        print(f"Erro ao enviar arquivo para o MinIO: {str(e)}")
        return None

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
