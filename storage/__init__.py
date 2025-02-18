"""
Pacote de gerenciamento de armazenamento usando MinIO.
Este pacote contém a implementação do sistema de armazenamento de arquivos.

Documentação:
- Upload e download de arquivos via MinIO
- Geração de URLs pré-assinadas para acesso temporário
- Suporte para múltiplos tipos de mídia (imagens, áudios, vídeos)
- Organização automática em diretórios por tipo
"""

from .minio_client import (
    upload_file,
    download_file,
    get_presigned_url,
    delete_file,
    list_files,
    check_minio_connection,
    get_minio_client,
    ensure_bucket
)

__all__ = [
    'upload_file',
    'download_file',
    'get_presigned_url',
    'list_files',
    'delete_file',
    'check_minio_connection',
    'get_minio_client',
    'ensure_bucket'
]

# Exporta as funções principais para uso direto
# Exemplo de uso:
# from storage import upload_file, get_presigned_url
# url = upload_file("arquivo.mp4", "videos/123.mp4")
# link = get_presigned_url("videos/123.mp4")
