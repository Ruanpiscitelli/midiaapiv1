"""
Configurações do Celery usando Pydantic.

Este módulo define os parâmetros necessários para:
- Conexão com broker Redis
- Configurações de tasks
- Configurações de workers
"""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class CelerySettings(BaseSettings):
    """Configurações do Celery."""
    
    # Configurações de broker
    broker_url: str = "redis://localhost:6379/0"
    result_backend: str = "redis://localhost:6379/0"
    
    # Configurações de tasks
    task_serializer: str = "json"
    result_serializer: str = "json"
    accept_content: List[str] = ["json"]
    task_track_started: bool = True
    task_time_limit: int = 18000  # 5 horas
    
    # Configurações de workers
    worker_prefetch_multiplier: int = 1
    worker_max_tasks_per_child: int = 50
    worker_max_memory_per_child: int = 1000000  # 1GB
    
    # Configurações de timezone
    enable_utc: bool = True
    timezone: str = "America/Sao_Paulo"
    
    # Configurações de retry
    task_default_retry_delay: int = 180  # 3 minutos
    task_max_retries: int = 3
    
    model_config = SettingsConfigDict(
        env_file=".env.celery",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    def get_config(self) -> dict:
        """Retorna configuração formatada para o Celery."""
        return {
            # Broker e Backend
            "broker_url": self.broker_url,
            "result_backend": self.result_backend,
            
            # Tasks
            "task_serializer": self.task_serializer,
            "result_serializer": self.result_serializer,
            "accept_content": self.accept_content,
            "task_track_started": self.task_track_started,
            "task_time_limit": self.task_time_limit,
            
            # Workers
            "worker_prefetch_multiplier": self.worker_prefetch_multiplier,
            "worker_max_tasks_per_child": self.worker_max_tasks_per_child,
            "worker_max_memory_per_child": self.worker_max_memory_per_child,
            
            # Timezone
            "enable_utc": self.enable_utc,
            "timezone": self.timezone,
            
            # Retry
            "task_default_retry_delay": self.task_default_retry_delay,
            "task_max_retries": self.task_max_retries
        }

# Instância global das configurações
celery_settings = CelerySettings() 