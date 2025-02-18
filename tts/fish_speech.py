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

from config import FISH_SPEECH_CONFIG, MODELS_CONFIG
from storage.minio_client import upload_file

class FishSpeechTTS:
    """Classe otimizada para síntese de voz usando Fish Speech."""
    
    def __init__(self):
        """Inicializa configurações básicas sem carregar o modelo."""
        # Configurações básicas
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.config = FISH_SPEECH_CONFIG
        self.model_dir = Path(self.config["model_path"])
        
        # Inicializa atributos
        self.model = None
        self.model_path = None
        self.loaded_voices: Dict[str, torch.Tensor] = {}
        
        # Verifica diretórios necessários
        self._ensure_directories()
        
        logger.info(f"Fish Speech V{self.config['version']} configurado para {self.device}")

    def _ensure_directories(self):
        """Garante que os diretórios necessários existem."""
        try:
            self.model_dir.mkdir(parents=True, exist_ok=True)
            (self.model_dir / "voices").mkdir(exist_ok=True)
            (self.model_dir / "custom_voices").mkdir(exist_ok=True)
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
        config_path = MODELS_CONFIG.get("fish_speech_model_path")
        if config_path:
            path = Path(config_path)
            if path.exists():
                logger.info(f"Usando modelo configurado em: {path}")
                return path
                
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
                    "Configure MODELS_CONFIG['fish_speech_model_path'] ou "
                    "coloque o modelo em um dos caminhos padrão."
                )
            
            # Carrega e otimiza o modelo
            self.model = torch.jit.load(self.model_path)
            self.model.to(self.device)
            self.model.eval()
            
            # Aplica otimizações se disponível CUDA
            if torch.cuda.is_available():
                if self.config["use_half"]:
                    self.model = self.model.half()
                if self.config["use_compile"]:
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
            if len(text) > self.config["max_text_length"]:
                raise ValueError(f"Texto muito longo. Máximo: {self.config['max_text_length']}")
            
            if language not in self.config["supported_languages"]:
                logger.warning(f"Idioma {language} não oficialmente suportado")
            
            # Carrega voz
            voice_model = self._load_voice(voice_name)
            if voice_model is None:
                raise ValueError(f"Voz {voice_name} não encontrada")
            
            # Configurações de geração
            temp = temperature or self.config["temperature"]
            
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
                self.config["sample_rate"]
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
            voice_path = self.model_dir / "voices" / f"{voice_name}.pth"
            
            # Valida apenas vozes pré-treinadas
            if voice_path.exists():
                if voice_name not in FISH_SPEECH_CONFIG["available_voices"]:
                    raise ValueError(f"Voz pré-treinada {voice_name} não disponível")
            else:
                # Para vozes customizadas, apenas verifica se o arquivo existe
                voice_path = self.model_dir / "custom_voices" / f"{voice_name}.pth"
            
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

# Instância global com inicialização lazy
tts = FishSpeechTTS()
