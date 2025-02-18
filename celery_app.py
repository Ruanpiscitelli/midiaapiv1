"""
Configuração do Celery para processamento assíncrono.

Este módulo configura o Celery para executar tarefas em background:
- Conexão com Redis como message broker
- Configuração dos workers (GPU e CPU)
- Registro das tarefas assíncronas
- Monitoramento via Flower
"""

import os
from celery import Celery
from celery.signals import worker_ready
from config import CELERY_CONFIG
import logging
from redis import Redis
from loguru import logger
import torch

# Configuração de logging
logger = logging.getLogger(__name__)

# Inicializa o Celery com o nome do módulo atual
app = Celery('simpleapi')

# Carrega configurações do config.py
app.conf.update(**CELERY_CONFIG)

# Configurações adicionais para otimização
app.conf.update(
    # Limita o número de tarefas que um worker pode pegar de uma vez
    # Importante para tarefas de GPU para evitar OOM
    worker_prefetch_multiplier=1,
    
    # Ativa monitoramento de tarefas iniciadas
    task_track_started=True,
    
    # Configurações de retry para tarefas que falham
    task_retry_delay_start=3,  # Espera inicial de 3 segundos
    task_max_retries=3,        # Máximo de 3 tentativas
    task_retry_exponential_backoff=True,  # Backoff exponencial
    
    # Configurações de logging
    worker_redirect_stdouts=False,  # Evita duplicação de logs
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s'
)

# Configurações específicas para tarefas de GPU
gpu_available = torch.cuda.is_available()
app.conf.task_routes = {
    'tasks.generate_image_task': {'queue': 'gpu' if gpu_available else 'cpu'},
    'tasks.generate_tts_task': {'queue': 'gpu' if gpu_available else 'cpu'},
    'tasks.generate_video_task': {'queue': 'cpu'}
}

# Configurações de concorrência por tipo de tarefa
app.conf.task_annotations = {
    'tasks.generate_image_task': {'rate_limit': '2/m'},  # Limita a 2 gerações por minuto
    'tasks.generate_tts_task': {'rate_limit': '10/m'},   # Limita a 10 gerações por minuto
    'tasks.generate_video_task': {'rate_limit': '5/m'}   # Limita a 5 gerações por minuto
}

# Evento disparado quando o worker está pronto
@worker_ready.connect
def on_worker_ready(sender, **kwargs):
    """Log quando o worker estiver pronto para processar tarefas."""
    logger.info(f"Worker {sender.hostname} pronto para processar tarefas")
    logger.info(f"Configurações: {app.conf}")

# Função para iniciar workers com configurações específicas
def start_worker(queue='default'):
    """
    Inicia um worker Celery com configurações específicas para a fila.
    
    Args:
        queue: Nome da fila ('gpu' ou 'cpu')
    """
    if queue == 'gpu':
        # Configurações para worker GPU
        app.worker_main([
            'worker',
            '--loglevel=INFO',
            '--queues=gpu',
            '--concurrency=1',  # Um worker por GPU
            '--pool=solo'       # Evita problemas com multiprocessing e CUDA
        ])
    else:
        # Configurações para worker CPU
        app.worker_main([
            'worker',
            '--loglevel=INFO',
            '--queues=cpu',
            '--concurrency=2',  # Dois workers para CPU
            '--pool=prefork'    # Pool padrão do Celery
        ])

def check_redis_connection() -> bool:
    """
    Verifica se a conexão com o Redis está funcionando.
    
    Returns:
        bool: True se a conexão está ok, False caso contrário
    """
    try:
        redis_client = Redis.from_url(CELERY_CONFIG["broker_url"])
        redis_client.ping()
        return True
    except Exception as e:
        logger.error(f"Erro ao verificar conexão com Redis: {str(e)}")
        return False

if __name__ == '__main__':
    # Se executado diretamente, inicia o worker
    import sys
    queue = sys.argv[1] if len(sys.argv) > 1 else 'default'
    start_worker(queue)
