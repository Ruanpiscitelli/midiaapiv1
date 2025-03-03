"""
Módulo otimizado de síntese de voz usando Fish Speech V1.4.
Referência: https://github.com/fishaudio/fish-speech
"""

import os
import torch
import torchaudio
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Union
import tempfile
import uuid
from loguru import logger
from torch.cuda import amp
from functools import lru_cache

from config import MODELS_CONFIG
from storage.minio_client import upload_file

class FishSpeechTTS:
    """Classe otimizada para síntese de voz usando Fish Speech."""
    
    def __init__(self):
        """Inicializa configurações básicas sem carregar o modelo."""
        # Configurações básicas
        self.device = torch.device(MODELS_CONFIG["device"])
        self.model_dir = Path(MODELS_CONFIG["fish_speech"]["model_path"])
        self.voice_dir = Path(MODELS_CONFIG["fish_speech"]["voice_dir"])
        self.custom_voice_dir = Path(MODELS_CONFIG["fish_speech"]["custom_voice_dir"])
        
        # Configurações do modelo
        self.sample_rate = MODELS_CONFIG["fish_speech"]["sample_rate"]
        self.max_text_length = MODELS_CONFIG["fish_speech"]["max_text_length"]
        self.temperature = MODELS_CONFIG["fish_speech"]["temperature"]
        self.use_half = MODELS_CONFIG["fish_speech"]["use_half"]
        self.use_compile = MODELS_CONFIG["fish_speech"]["use_compile"]
        
        # Configurações de idiomas e vozes
        self.supported_languages = MODELS_CONFIG["fish_speech"]["supported_languages"]
        self.available_voices = MODELS_CONFIG["fish_speech"]["available_voices"]
        
        # Inicializa atributos
        self.model = None
        self.model_path = None
        self.loaded_voices: Dict[str, torch.Tensor] = {}
        
        # Verifica diretórios necessários
        self._ensure_directories()
        
        logger.info(f"Fish Speech configurado para {self.device}")

    def _ensure_directories(self):
        """Garante que os diretórios necessários existem."""
        try:
            self.model_dir.mkdir(parents=True, exist_ok=True)
            self.voice_dir.mkdir(parents=True, exist_ok=True)
            self.custom_voice_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Erro ao criar diretórios: {e}")
            raise RuntimeError("Não foi possível criar diretórios necessários") from e

    @lru_cache(maxsize=1)
    def _get_model_path(self) -> Path:
        """
        Obtém o caminho do modelo, com cache para evitar buscas repetidas.
        
        Returns:
            Path: Caminho para o arquivo do modelo
        """
        # Tenta obter da configuração
        model_path = Path(MODELS_CONFIG["fish_speech"]["model_path"]) / "model.pth"
        if model_path.exists():
            logger.info(f"Usando modelo configurado em: {model_path}")
            return model_path
                
        # Tenta caminhos padrão
        default_paths = [
            self.model_dir / "model.pth",
            Path("/workspace/midiaapiv1/models/fish_speech/model.pth"),
            Path("models/fish_speech/model.pth"),
            Path(os.path.expanduser("~/.cache/fish_speech/model.pth"))
        ]
        
        for path in default_paths:
            if path.exists():
                logger.info(f"Modelo encontrado em: {path}")
                return path
                
        # Se nenhum caminho funcionar, retorna o padrão
        default_path = self.model_dir / "model.pth"
        logger.warning(f"Modelo não encontrado. Será necessário em: {default_path}")
        return default_path

    def ensure_model_loaded(self):
        """
        Garante que o modelo está carregado antes do uso.
        Raises:
            RuntimeError: Se não for possível carregar o modelo
        """
        if self.model is not None:
            return
            
        try:
            # Obtém caminho do modelo
            self.model_path = self._get_model_path()
            
            if not self.model_path.exists():
                raise FileNotFoundError(
                    f"Modelo não encontrado em: {self.model_path}\n"
                    "Configure MODELS_CONFIG['fish_speech']['model_path'] ou "
                    "coloque o modelo em um dos caminhos padrão."
                )
            
            # Carrega e otimiza o modelo
            self.model = torch.jit.load(self.model_path)
            self.model.to(self.device)
            self.model.eval()
            
            # Aplica otimizações se disponível CUDA
            if torch.cuda.is_available():
                if self.use_half:
                    self.model = self.model.half()
                if self.use_compile:
                    self.model = torch.compile(self.model)
                    
            logger.info(f"Modelo carregado e otimizado em: {self.device}")
            
        except Exception as e:
            self.model = None
            logger.error(f"Erro ao carregar modelo: {e}")
            raise RuntimeError("Falha ao carregar modelo FishSpeech") from e

    def generate_speech(self, text: str, **kwargs):
        """Wrapper para garantir que o modelo está carregado antes de gerar áudio."""
        self.ensure_model_loaded()
        return self._generate_speech(text, **kwargs)

    def _generate_speech(self, text: str, voice_name: str = "default", language: str = "pt-BR", temperature: float = None, output_path: Optional[str] = None):
        """Implementação real da geração de áudio."""
        try:
            # Validações
            if len(text) > self.max_text_length:
                raise ValueError(f"Texto muito longo. Máximo: {self.max_text_length}")
            
            if language not in self.supported_languages:
                logger.warning(f"Idioma {language} não oficialmente suportado")
            
            # Carrega voz
            voice_model = self._load_voice(voice_name)
            if voice_model is None:
                raise ValueError(f"Voz {voice_name} não encontrada")
            
            # Configurações de geração
            temp = temperature or self.temperature
            
            # Gera áudio com otimizações
            with amp.autocast(enabled=torch.cuda.is_available()):
                waveform = self.model.forward(
                    text=text,
                    voice=voice_model,
                    temperature=temp
                )
            
            # Define caminho de saída
            if output_path is None:
                output_path = str(Path(tempfile.gettempdir()) / f"tts_{uuid.uuid4()}.wav")
            
            # Salva áudio
            torchaudio.save(
                output_path,
                waveform.cpu(),
                self.sample_rate
            )
            
            # Limpa cache CUDA
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            return output_path
            
        except Exception as e:
            logger.error(f"Erro na geração: {str(e)}")
            return None

    def _load_voice(self, voice_name: str) -> Optional[torch.Tensor]:
        """Carrega um modelo de voz específico."""
        if voice_name in self.loaded_voices:
            return self.loaded_voices[voice_name]
        
        try:
            # Procura primeiro nas vozes pré-treinadas
            voice_path = self.voice_dir / f"{voice_name}.pth"
            
            # Valida apenas vozes pré-treinadas
            if voice_path.exists():
                if voice_name not in self.available_voices:
                    raise ValueError(f"Voz pré-treinada {voice_name} não disponível")
            else:
                # Para vozes customizadas, apenas verifica se o arquivo existe
                voice_path = self.custom_voice_dir / f"{voice_name}.pth"
            
            if not voice_path.exists():
                raise FileNotFoundError(f"Voz {voice_name} não encontrada")
            
            voice_model = torch.load(voice_path, map_location=self.device)
            self.loaded_voices[voice_name] = voice_model
            logger.info(f"Voz {voice_name} carregada com sucesso")
            return voice_model
        
        except Exception as e:
            logger.error(f"Erro ao carregar voz {voice_name}: {str(e)}")
            return None

    def generate_and_upload(
        self,
        text: str,
        job_id: str,
        voice_name: str = "default",
        language: str = "pt-BR"
    ) -> Optional[str]:
        """
        Gera o áudio e faz upload para o MinIO.
        """
        try:
            # Gera o áudio
            audio_path = self.generate_speech(text, voice_name, language)
            if audio_path is None:
                raise RuntimeError("Falha na geração do áudio")

            # Faz upload para o MinIO
            object_name = f"audio/{job_id}.wav"
            url = upload_file(audio_path, object_name)

            # Remove o arquivo temporário
            if os.path.exists(audio_path):
                os.remove(audio_path)

            return url

        except Exception as e:
            logger.error(f"Erro no processo de geração e upload: {str(e)}")
            return None

def generate_tts(
    text: str,
    job_id: str,
    voice_name: str = "default",
    language: str = "pt-BR"
) -> Optional[str]:
    """
    Função de alto nível para geração de TTS e upload do áudio.
    
    Args:
        text: Texto para converter em fala
        job_id: ID único do job para nomear o arquivo
        voice_name: Nome da voz a ser usada (default ou custom)
        language: Código do idioma (ex: pt-BR, en-US)
        
    Returns:
        Optional[str]: URL do arquivo de áudio gerado ou None em caso de erro
    """
    try:
        # Valida parâmetros
        if not text or not job_id:
            raise ValueError("Texto e job_id são obrigatórios")
            
        # Usa a instância global para gerar e fazer upload
        url = tts.generate_and_upload(
            text=text,
            job_id=job_id,
            voice_name=voice_name,
            language=language
        )
        
        if not url:
            raise RuntimeError("Falha ao gerar ou fazer upload do áudio")
            
        logger.info(f"Áudio gerado com sucesso: {url}")
        return url
        
    except Exception as e:
        logger.error(f"Erro em generate_tts: {str(e)}")
        return None

# Instância global com inicialização lazy
tts = FishSpeechTTS()
