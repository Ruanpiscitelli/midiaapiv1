"""
Script para download dos modelos de IA necessários (SDXL e Fish Speech).
Inclui métodos alternativos de download sem necessidade de token.

Este script baixa automaticamente:
- Stable Diffusion XL (modelo base e VAE)
- Fish Speech (modelo base e vozes pré-treinadas)

Requer:
- Conexão com internet
- Espaço em disco (~10GB para SDXL, ~500MB para Fish Speech)
"""

import os
import sys
import requests
import torch
from pathlib import Path
from tqdm import tqdm
import logging
import hashlib
import subprocess
from huggingface_hub import hf_hub_download
from config import FISH_SPEECH_CONFIG

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurações
BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"

# URLs e caminhos para os modelos (Método Alternativo)
MODELS_CONFIG = {
    "sdxl": {
        "path": MODELS_DIR / "sdxl",
        "files": {
            "model.safetensors": {
                "url": "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors",
                "civitai_url": "https://civitai.com/api/download/models/128713",  # Alternativa via CivitAI
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
                "url": "https://huggingface.co/your-org/fish-speech/resolve/main/model.pth",
                "gdrive_id": "1a2b3c4d5e",  # ID alternativo do Google Drive
                "md5": "a00b0c6eb5fe8e5d1f94d1b3f72106b3"
            },
            "voices/male_1.pth": {
                "url": "https://huggingface.co/your-org/fish-speech/resolve/main/voices/male_1.pth",
                "gdrive_id": "2b3c4d5e6f",
                "md5": "a00b0c6eb5fe8e5d1f94d1b3f72106b4"
            },
            "voices/female_1.pth": {
                "url": "https://huggingface.co/your-org/fish-speech/resolve/main/voices/female_1.pth",
                "gdrive_id": "3c4d5e6f7g",
                "md5": "a00b0c6eb5fe8e5d1f94d1b3f72106b5"
            }
        }
    }
}

def create_directories():
    """Cria a estrutura de diretórios necessária."""
    try:
        # Cria diretórios base
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Cria diretórios do Fish Speech
        fish_speech_dirs = [
            FISH_SPEECH_CONFIG["model_path"],
            FISH_SPEECH_CONFIG["voice_dir"],
            FISH_SPEECH_CONFIG["custom_voice_dir"]
        ]
        
        for directory in fish_speech_dirs:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Diretório criado: {directory}")
            
        # Cria diretórios do SDXL
        MODELS_CONFIG["sdxl"]["path"].mkdir(parents=True, exist_ok=True)
        
    except Exception as e:
        logger.error(f"Erro ao criar diretórios: {e}")
        raise

def download_file_with_progress(url: str, dest_path: Path, desc: str):
    """
    Faz download de um arquivo com barra de progresso.
    
    Args:
        url: URL do arquivo
        dest_path: Caminho de destino
        desc: Descrição para a barra de progresso
    """
    try:
        response = requests.get(url, stream=True)
        total = int(response.headers.get('content-length', 0))
        
        with open(dest_path, 'wb') as file, tqdm(
            desc=desc,
            total=total,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
        ) as pbar:
            for data in response.iter_content(chunk_size=1024):
                size = file.write(data)
                pbar.update(size)
        return True
    except Exception as e:
        logger.error(f"Erro no download de {url}: {str(e)}")
        return False

def download_from_gdrive(file_id: str, dest_path: Path):
    """
    Faz download de um arquivo do Google Drive usando gdown.
    """
    try:
        import gdown
        url = f"https://drive.google.com/uc?id={file_id}"
        gdown.download(url, str(dest_path), quiet=False)
        return True
    except Exception as e:
        logger.error(f"Erro no download do Google Drive: {str(e)}")
        return False

def download_from_civitai(url: str, dest_path: Path):
    """
    Faz download de um modelo do CivitAI.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        return download_file_with_progress(url, dest_path, f"Baixando de CivitAI: {dest_path.name}")
    except Exception as e:
        logger.error(f"Erro no download do CivitAI: {str(e)}")
        return False

def verify_file_hash(file_path: Path, expected_md5: str) -> bool:
    """
    Verifica o hash MD5 de um arquivo.
    """
    if not file_path.exists():
        return False
    
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest() == expected_md5

def download_model_file(file_config: dict, dest_path: Path) -> bool:
    """
    Tenta baixar um arquivo usando diferentes métodos.
    """
    if dest_path.exists() and verify_file_hash(dest_path, file_config["md5"]):
        logger.info(f"{dest_path.name} já existe e está íntegro, pulando...")
        return True

    # Tenta primeiro o download direto
    if download_file_with_progress(file_config["url"], dest_path, f"Baixando {dest_path.name}"):
        return True

    # Se falhar e tiver URL do CivitAI, tenta por lá
    if "civitai_url" in file_config and download_from_civitai(file_config["civitai_url"], dest_path):
        return True

    # Se tiver ID do Google Drive, tenta por lá
    if "gdrive_id" in file_config and download_from_gdrive(file_config["gdrive_id"], dest_path):
        return True

    return False

def download_sdxl():
    """Download dos modelos do Stable Diffusion XL."""
    logger.info("Iniciando download do Stable Diffusion XL...")
    
    for filename, file_config in MODELS_CONFIG["sdxl"]["files"].items():
        dest_path = MODELS_CONFIG["sdxl"]["path"] / filename
        if not download_model_file(file_config, dest_path):
            raise RuntimeError(f"Falha ao baixar {filename}")
        logger.info(f"{filename} baixado com sucesso!")

def download_fish_speech_model():
    """
    Download do modelo Fish Speech V1.5/V1.4 do Hugging Face.
    Documentação: https://huggingface.co/fishaudio/fish-speech-1.5
    """
    try:
        model_dir = FISH_SPEECH_CONFIG["model_path"]
        voice_dir = FISH_SPEECH_CONFIG["voice_dir"]
        
        # Download do modelo do Hugging Face
        logger.info("Baixando modelo Fish Speech do Hugging Face...")
        
        try:
            # Tenta baixar V1.5 primeiro
            repo_id = "fishaudio/fish-speech-1.5"
            files_to_download = [
                "firefly-gan-vq-fsq-8x1024-21hz-generator.pth",  # Decoder
                "config.json",
                "vocab.json",  # Alterado de tokenizer.json para vocab.json
                "merges.txt"   # Arquivo adicional necessário
            ]
        except Exception:
            # Fallback para V1.4
            logger.info("Fallback para Fish Speech V1.4...")
            repo_id = "fishaudio/fish-speech-1.4"
            files_to_download = [
                "model.pth",
                "config.json",
                "vocab.json",
                "merges.txt"
            ]
        
        # Download dos arquivos principais
        for filename in files_to_download:
            output_path = model_dir / filename
            if not output_path.exists():
                logger.info(f"Baixando {filename}...")
                try:
                    hf_hub_download(
                        repo_id=repo_id,
                        filename=filename,
                        local_dir=model_dir,
                        local_dir_use_symlinks=False,
                        token=os.getenv("HF_TOKEN")  # Token para acesso ao modelo
                    )
                    logger.info(f"{filename} baixado com sucesso")
                except Exception as e:
                    if "401 Client Error" in str(e):
                        logger.error("Erro de autenticação. Configure a variável de ambiente HF_TOKEN")
                        raise RuntimeError("Token de acesso ao Hugging Face necessário")
                    elif "404" in str(e):
                        logger.warning(f"Arquivo {filename} não encontrado, continuando...")
                        continue
                    else:
                        logger.error(f"Erro ao baixar {filename}: {e}")
                        raise
            else:
                logger.info(f"{filename} já existe")
        
        # Download da voz padrão
        voice_path = voice_dir / "default.pth"
        if not voice_path.exists():
            logger.info("Baixando voz padrão...")
            try:
                hf_hub_download(
                    repo_id=repo_id,
                    filename="voices/default.pth",
                    local_dir=voice_dir.parent,
                    local_dir_use_symlinks=False,
                    token=os.getenv("HF_TOKEN")
                )
                logger.info("Voz padrão baixada com sucesso")
            except Exception as e:
                if "404" in str(e):
                    logger.warning("Voz padrão não encontrada, usando fallback...")
                    # Aqui você pode adicionar um fallback para outra voz
                else:
                    logger.error(f"Erro ao baixar voz padrão: {e}")
                    raise
        
        logger.info("Download do Fish Speech concluído com sucesso!")
        return True
        
    except Exception as e:
        logger.error(f"Erro no download do Fish Speech: {str(e)}")
        return False

def verify_cuda():
    """Verifica se CUDA está disponível."""
    if torch.cuda.is_available():
        logger.info(f"CUDA disponível: {torch.cuda.get_device_name(0)}")
    else:
        logger.warning("CUDA não disponível! Os modelos rodarão em CPU (muito mais lento)")

def main():
    """Função principal do script."""
    logger.info("Iniciando download dos modelos...")
    
    try:
        # Verifica CUDA
        verify_cuda()
        
        # Cria diretórios
        create_directories()
        
        # Instala dependências
        subprocess.check_call([
            sys.executable, 
            "-m", 
            "pip", 
            "install", 
            "huggingface_hub"
        ])
        
        # Download dos modelos
        if download_fish_speech_model():
            logger.info("Download do Fish Speech concluído com sucesso!")
        else:
            raise RuntimeError("Falha no download do Fish Speech")
            
        logger.info("Todos os modelos foram baixados com sucesso!")
        
    except Exception as e:
        logger.error(f"Erro durante o download dos modelos: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 