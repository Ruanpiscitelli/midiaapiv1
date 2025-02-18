"""
Módulo de banco de dados SQLite com suporte a migrações Alembic.
Este módulo gerencia a conexão com o banco de dados e as operações CRUD.

Documentação:
- Usa SQLite como banco de dados
- Suporta migrações via Alembic
- Mantém logs de jobs e seus status
- Thread-safe para uso com FastAPI
"""

import os
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from contextlib import contextmanager
from loguru import logger

from config import DATABASE_CONFIG

# Configuração de logging
logger = logging.getLogger(__name__)

# Caminho do banco de dados
DB_PATH = DATABASE_CONFIG["url"].replace("sqlite:///", "")
DB_DIR = os.path.dirname(DB_PATH)

# Garante que o diretório do banco existe
os.makedirs(DB_DIR, exist_ok=True)

def dict_factory(cursor: sqlite3.Cursor, row: tuple) -> Dict:
    """Converte rows do SQLite para dicionários."""
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}

@contextmanager
def get_connection():
    """
    Gerencia conexões com o banco de dados de forma segura.
    Usa context manager para garantir que a conexão seja fechada corretamente.
    """
    conn = None
    try:
        conn = sqlite3.connect(
            DB_PATH,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            check_same_thread=False,  # Necessário para FastAPI
            timeout=30  # Timeout para evitar deadlocks
        )
        conn.row_factory = dict_factory
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Erro na conexão com o banco: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

def create_tables():
    """
    Cria as tabelas necessárias no banco de dados.
    Esta função é chamada na inicialização do aplicativo.
    """
    with get_connection() as conn:
        # Tabela de jobs
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                result_url TEXT,
                error_message TEXT,
                metadata TEXT  -- JSON com dados adicionais
            )
        """)

        # Tabela de arquivos gerados
        conn.execute("""
            CREATE TABLE IF NOT EXISTS generated_files (
                file_id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                file_type TEXT NOT NULL,  -- 'image', 'audio', 'video'
                file_url TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES jobs(job_id)
                    ON DELETE CASCADE
            )
        """)

        # Trigger para atualizar updated_at
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS update_job_timestamp 
            AFTER UPDATE ON jobs
            BEGIN
                UPDATE jobs SET updated_at = CURRENT_TIMESTAMP 
                WHERE job_id = NEW.job_id;
            END;
        """)

        logger.info("Tabelas criadas/verificadas com sucesso")

def store_job(job_id: str, status: str) -> None:
    """
    Registra um novo job no banco de dados.
    
    Args:
        job_id: ID único do job
        status: Estado inicial ('queued', 'processing', 'completed', 'failed')
    """
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO jobs (job_id, status) VALUES (?, ?)",
            (job_id, status)
        )
        logger.info(f"Job {job_id} registrado com status {status}")

def update_job_status(job_id: str, status: str, result_url: Optional[str] = None) -> None:
    """
    Atualiza o status de um job existente.
    
    Args:
        job_id: ID do job
        status: Novo status
        result_url: URL do resultado (opcional)
    """
    with get_connection() as conn:
        if result_url:
            conn.execute(
                "UPDATE jobs SET status = ?, result_url = ? WHERE job_id = ?",
                (status, result_url, job_id)
            )
        else:
            conn.execute(
                "UPDATE jobs SET status = ? WHERE job_id = ?",
                (status, job_id)
            )
        logger.info(f"Job {job_id} atualizado para status {status}")

def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Recupera o status atual de um job.
    
    Args:
        job_id: ID do job
    
    Returns:
        Dict com informações do job ou None se não encontrado
    """
    with get_connection() as conn:
        result = conn.execute(
            "SELECT * FROM jobs WHERE job_id = ?",
            (job_id,)
        ).fetchone()
        
        if result:
            # Busca arquivos associados
            files = conn.execute(
                "SELECT * FROM generated_files WHERE job_id = ?",
                (job_id,)
            ).fetchall()
            
            result['files'] = files
            
        return result

def store_generated_file(job_id: str, file_type: str, file_url: str) -> None:
    """
    Registra um arquivo gerado para um job.
    
    Args:
        job_id: ID do job
        file_type: Tipo do arquivo ('image', 'audio', 'video')
        file_url: URL do arquivo no MinIO
    """
    with get_connection() as conn:
        file_id = f"{job_id}_{file_type}_{datetime.now().timestamp()}"
        conn.execute(
            """
            INSERT INTO generated_files (file_id, job_id, file_type, file_url)
            VALUES (?, ?, ?, ?)
            """,
            (file_id, job_id, file_type, file_url)
        )
        logger.info(f"Arquivo {file_type} registrado para job {job_id}")

def delete_old_jobs(days: int = 7) -> None:
    """
    Remove jobs antigos do banco de dados.
    
    Args:
        days: Número de dias após os quais os jobs são considerados antigos
    """
    cutoff_date = datetime.now() - timedelta(days=days)
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM jobs WHERE created_at < ?",
            (cutoff_date,)
        )
        logger.info(f"Jobs mais antigos que {days} dias foram removidos")

def check_database_connection() -> bool:
    """
    Verifica se a conexão com o banco de dados está funcionando.
    
    Returns:
        bool: True se a conexão está ok, False caso contrário
    """
    try:
        conn = sqlite3.connect('db/logs.db')
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        cursor.fetchone()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao verificar conexão com banco de dados: {str(e)}")
        return False

# Cria as tabelas ao iniciar o módulo
create_tables()

# Executa limpeza de jobs antigos
delete_old_jobs()
