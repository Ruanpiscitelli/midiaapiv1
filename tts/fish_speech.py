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

from config import FISH_SPEECH_CONFIG, MODELS_CONFIG
from storage.minio_client import upload_file

class FishSpeechTTS:
    """Classe otimizada para síntese de voz usando Fish Speech."""
    
    def __init__(self):
        """Inicializa o modelo com otimizações."""
        try:
            # Configurações básicas
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.config = FISH_SPEECH_CONFIG
            self.model_dir = Path(self.config["model_path"])
            
            # Inicializa atributos
            self.model = None
            self.model_path = self._get_model_path()
            
            # Carrega modelo
            self._load_base_model()
            
            # Cache de vozes
            self.loaded_voices: Dict[str, torch.Tensor] = {}
            
            logger.info(f"Fish Speech V{self.config['version']} inicializado no {self.device}")
            
        except Exception as e:
            logger.error(f"Erro na inicialização: {str(e)}")
            raise RuntimeError("Falha ao inicializar FishSpeechTTS") from e

    def _get_model_path(self) -> Path:
        """
        Obtém o caminho do modelo, primeiro checando a configuração,
        depois o caminho padrão
        
        Returns:
            Path: Caminho para o arquivo do modelo
        """
        # Tenta obter da configuração
        config_path = MODELS_CONFIG.get("fish_speech_model_path")
        if config_path:
            path = Path(config_path)
            if path.exists():
                return path
                
        # Tenta caminhos padrão
        default_paths = [
            self.model_dir / "model.pth",  # Primeiro tenta no diretório configurado
            Path("/workspace/midiaapiv1/models/fish_speech/model.pth"),
            Path("models/fish_speech/model.pth"),
            Path(os.path.expanduser("~/.cache/fish_speech/model.pth"))
        ]
        
        for path in default_paths:
            if path.exists():
                logger.info(f"Modelo encontrado em: {path}")
                return path
                
        # Se nenhum caminho funcionar, usa o caminho do diretório configurado
        logger.warning(f"Modelo não encontrado nos caminhos padrão. Usando: {default_paths[0]}")
        return default_paths[0]
    
    def _load_base_model(self):
        """Carrega e otimiza o modelo base."""
        try:
            if not self.model_path.exists():
                raise FileNotFoundError(
                    f"Arquivo do modelo não encontrado em: {self.model_path}\n"
                    "Por favor, configure MODELS_CONFIG['fish_speech_model_path'] "
                    "ou coloque o modelo em um dos caminhos padrão."
                )
                
            # Carrega modelo
            self.model = torch.jit.load(self.model_path)
            self.model.to(self.device)
            self.model.eval()
            
            # Otimizações
            if torch.cuda.is_available():
                if self.config["use_half"]:
                    self.model = self.model.half()
                if self.config["use_compile"]:
                    self.model = torch.compile(self.model)
                    
            logger.info(f"Modelo base carregado e otimizado em: {self.device}")
            
        except Exception as e:
            logger.error(f"Erro ao carregar modelo FishSpeech: {e}")
            raise RuntimeError("Falha ao inicializar FishSpeechTTS") from e

    @torch.no_grad()
    @amp.autocast(enabled=True)
    def generate_speech(
        self,
        text: str,
        voice_name: str = "default",
        language: str = "pt-BR",
        temperature: float = None,
        output_path: Optional[str] = None
    ) -> Optional[str]:
        """Gera áudio com otimizações de performance."""
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

# Instância global
tts = FishSpeechTTS()
