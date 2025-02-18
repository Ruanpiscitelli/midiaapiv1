"""
Configurações base do sistema.
Contém configurações fundamentais e caminhos importantes.
"""

import os
from pathlib import Path

class BaseSettings:
    # Informações da API
    API_VERSION = "2.0"
    API_TITLE = "Gerador de Vídeos com IA"
    API_KEY = os.getenv("API_KEY", "seu-token-secreto")
    DEBUG = bool(os.getenv("DEBUG", "True"))
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    
    # Diretórios principais
    BASE_DIR = Path(__file__).parent.parent
    MODELS_DIR = BASE_DIR / "models"
    TEMP_DIR = BASE_DIR / "temp"
    
    def __init__(self):
        # Garante que os diretórios existam
        self.MODELS_DIR.mkdir(exist_ok=True)
        self.TEMP_DIR.mkdir(exist_ok=True)

# Instancia as configurações
base_settings = BaseSettings()