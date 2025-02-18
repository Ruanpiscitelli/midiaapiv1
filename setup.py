"""
Script de setup para o projeto.
Gerencia a instalação, verificação de ambiente e download de modelos.
"""

import os
import sys
import subprocess
import hashlib
from pathlib import Path
import shutil
import json
from typing import Dict, Any
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Diretórios base
BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"
VENV_DIR = BASE_DIR / "venv"

# Adicione esta constante no início do arquivo junto com as outras
DEFAULT_ENV_CONTENT = """# Configurações do Servidor
HOST=0.0.0.0
PORT=8000
WORKERS=4
LOG_LEVEL=info

# Configurações de Segurança
SECRET_KEY=sua_chave_secreta_aqui
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Configurações do Banco de Dados
DATABASE_URL=sqlite:///./db/database.sqlite

# Configurações de Cache
REDIS_URL=redis://localhost:6379

# Configurações de Storage
STORAGE_TYPE=local  # local ou minio
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false

# Configurações de IA
MODEL_PATH=./models
CUDA_VISIBLE_DEVICES=0,1,2,3
HF_TOKEN=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
"""

# Configuração dos modelos e seus hashes MD5
MODELS_CONFIG = {
    "sdxl": {
        "path": MODELS_DIR / "sdxl",
        "files": {
            "model.safetensors": {
                "url": "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors",
                "md5": "a00b0c6eb5fe8e5d1f94d1b3f72106b1"
            },
            "vae.safetensors": {
                "url": "https://huggingface.co/madebyollin/sdxl-vae-fp16-fix/resolve/main/diffusion_pytorch_model.safetensors",
                "md5": "a00b0c6eb5fe8e5d1f94d1b3f72106b2"
            }
        }
    },
    "fish_speech": {
        "path": MODELS_DIR / "fish_speech",
        "files": {
            "model.pth": {
                "url": "https://huggingface.co/fish-speech/fish-speech-v1/resolve/main/model.pth",
                "md5": "a00b0c6eb5fe8e5d1f94d1b3f72106b3"
            }
        }
    }
}

def check_python_version() -> bool:
    """Verifica se a versão do Python é compatível."""
    return sys.version_info >= (3, 10)

def check_system_dependencies() -> bool:
    """Verifica dependências do sistema."""
    try:
        # Verifica FFmpeg
        subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True)
        
        # Verifica CUDA
        import torch
        if not torch.cuda.is_available():
            logger.warning("CUDA não disponível - GPU não será utilizada")
            
        # Verifica Docker (opcional)
        try:
            subprocess.run(["docker", "--version"], check=True, capture_output=True)
        except Exception:
            logger.warning("Docker não encontrado - alguns recursos podem estar indisponíveis")
        
        return True
    except Exception as e:
        logger.error(f"Erro ao verificar dependências: {str(e)}")
        return False

def setup_virtual_env() -> bool:
    """Cria e configura o ambiente virtual."""
    try:
        if not VENV_DIR.exists():
            logger.info("Criando ambiente virtual...")
            subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)

        # Determina o pip do ambiente virtual
        pip_path = VENV_DIR / "bin" / "pip" if os.name != "nt" else VENV_DIR / "Scripts" / "pip.exe"
        
        # Instala huggingface_hub primeiro
        subprocess.run([str(pip_path), "install", "--upgrade", "pip"], check=True)
        subprocess.run([str(pip_path), "install", "huggingface_hub"], check=True)
        subprocess.run([str(pip_path), "install", "-r", "requirements.txt"], check=True)
        
        return True
    except Exception as e:
        logger.error(f"Erro ao configurar ambiente virtual: {str(e)}")
        return False

def verify_file_hash(file_path: Path, expected_hash: str) -> bool:
    """Verifica o hash MD5 de um arquivo."""
    if not file_path.exists():
        return False
    
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest() == expected_hash

def download_model_file(url: str, file_path: Path) -> bool:
    """Baixa um arquivo de modelo."""
    try:
        import requests
        
        # Obter token do ambiente ou solicitar login
        token = os.getenv("HF_TOKEN")
        if not token:
            logger.info("Token HF não encontrado. Tentando login...")
            subprocess.run(["huggingface-cli", "login"], check=True)
            
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        
        response = requests.get(url, stream=True, headers=headers)
        response.raise_for_status()
        
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        logger.error(f"Erro ao baixar modelo: {str(e)}")
        return False

def setup_models() -> bool:
    """Configura os modelos de IA."""
    try:
        for model_name, model_config in MODELS_CONFIG.items():
            logger.info(f"Configurando modelo {model_name}...")
            model_config["path"].mkdir(parents=True, exist_ok=True)
            
            for file_name, file_config in model_config["files"].items():
                file_path = model_config["path"] / file_name
                if not verify_file_hash(file_path, file_config["md5"]):
                    logger.info(f"Baixando {file_name}...")
                    if not download_model_file(file_config["url"], file_path):
                        return False
                else:
                    logger.info(f"{file_name} já existe e está íntegro.")
        return True
    except Exception as e:
        logger.error(f"Erro ao configurar modelos: {str(e)}")
        return False

def setup_database() -> bool:
    """Configura o banco de dados."""
    try:
        # Cria diretório do banco
        db_dir = BASE_DIR / "db"
        db_dir.mkdir(exist_ok=True)

        # Aplica migrações
        subprocess.run(["alembic", "upgrade", "head"], check=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Erro ao configurar banco de dados: {str(e)}")
        return False

def create_env_file() -> bool:
    """Cria arquivo .env com configurações padrão."""
    try:
        env_path = BASE_DIR / ".env"
        if not env_path.exists():
            logger.info("Criando novo arquivo .env com configurações padrão...")
            with open(env_path, "w") as f:
                f.write(DEFAULT_ENV_CONTENT)
            logger.info("Arquivo .env criado com sucesso")
        return True
    except Exception as e:
        logger.error(f"Erro ao criar arquivo .env: {str(e)}")
        return False

def main():
    """Função principal de setup."""
    logger.info("Iniciando setup do projeto...")

    # Verifica versão do Python
    if not check_python_version():
        logger.error("Python 3.10 ou superior é necessário!")
        sys.exit(1)

    # Verifica dependências do sistema
    if not check_system_dependencies():
        logger.error("Dependências do sistema não atendidas!")
        sys.exit(1)

    # Setup do ambiente virtual
    if not setup_virtual_env():
        logger.error("Falha ao configurar ambiente virtual!")
        sys.exit(1)

    # Cria arquivo .env
    if not create_env_file():
        logger.error("Falha ao criar arquivo .env!")
        sys.exit(1)

    # Setup dos modelos
    if not setup_models():
        logger.error("Falha ao configurar modelos!")
        sys.exit(1)

    # Setup do banco de dados
    if not setup_database():
        logger.error("Falha ao configurar banco de dados!")
        sys.exit(1)

    logger.info("Setup concluído com sucesso!")

if __name__ == "__main__":
    main() 