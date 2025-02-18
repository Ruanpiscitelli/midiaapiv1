"""
Configurações do banco de dados usando Pydantic.

Este módulo define os parâmetros necessários para:
- Conexão com o banco de dados
- Pool de conexões
- Configurações de timeout
"""

from typing import Dict, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class DatabaseSettings(BaseSettings):
    """Configurações do banco de dados."""
    
    # Configurações de conexão
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "5432"))
    database: str = os.getenv("DB_NAME", "midiaapiv1")
    username: str = os.getenv("DB_USER", "postgres")
    password: str = os.getenv("DB_PASSWORD", "postgres")
    
    # String de conexão
    url: Optional[str] = None
    
    # Configurações do pool
    pool_size: int = 20
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 1800
    
    # Configurações de timeout
    connect_timeout: int = 10
    command_timeout: int = 30
    
    # Configurações de SSL
    ssl_mode: str = "prefer"
    ssl_cert: Optional[str] = None
    
    # Configurações de debug
    echo: bool = False
    echo_pool: bool = False
    
    model_config = SettingsConfigDict(
        env_file=".env.database",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Constrói a URL de conexão se não fornecida
        if not self.url:
            self.url = (
                f"postgresql://{self.username}:{self.password}@"
                f"{self.host}:{self.port}/{self.database}"
            )
            
    def get_config(self) -> dict:
        """Retorna configuração formatada para SQLAlchemy."""
        return {
            # Conexão principal
            "url": self.url,
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "username": self.username,
            "password": self.password,
            
            # Configurações de pool
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "pool_timeout": self.pool_timeout,
            "pool_recycle": self.pool_recycle,
            
            # Configurações de timeout
            "connect_timeout": self.connect_timeout,
            "command_timeout": self.command_timeout,
            
            # Configurações de SSL
            "ssl_mode": self.ssl_mode,
            "ssl_cert": self.ssl_cert,
            
            # Configurações de debug
            "echo": self.echo,
            "echo_pool": self.echo_pool,
            
            # Configurações do SQLAlchemy
            "sqlalchemy": {
                "pool_size": self.pool_size,
                "max_overflow": self.max_overflow,
                "pool_timeout": self.pool_timeout,
                "pool_recycle": self.pool_recycle,
                "echo": self.echo,
                "echo_pool": self.echo_pool
            }
        }

# Instância global das configurações
database_settings = DatabaseSettings() 