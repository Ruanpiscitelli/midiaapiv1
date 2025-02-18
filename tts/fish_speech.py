"""
Módulo de síntese de voz usando Fish Speech.

Este módulo implementa a geração de voz sintética usando o modelo Fish Speech.
Suporta múltiplas vozes pré-treinadas e clonagem de voz a partir de amostras.
"""

import os
import json
import torch
import torchaudio
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Union
import tempfile
import uuid
from loguru import logger

from config import FISH_SPEECH_CONFIG
from storage.minio_client import upload_file

class FishSpeechTTS:
    """Classe principal para síntese de voz usando Fish Speech."""
    
    def __init__(self):
        """Inicializa o modelo Fish Speech e carrega configurações."""
        try:
            # Configurações básicas
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model = None
            self.tokenizer = None
            self.loaded_voices: Dict[str, torch.Tensor] = {}
            
            # Carrega configurações
            self.model_dir = Path(FISH_SPEECH_CONFIG["model_path"])
            self.sample_rate = FISH_SPEECH_CONFIG["sample_rate"]
            self.max_text_length = FISH_SPEECH_CONFIG.get("max_text_length", 1000)
            self.batch_size = FISH_SPEECH_CONFIG.get("batch_size", 1)
            self.temperature = FISH_SPEECH_CONFIG.get("temperature", 0.8)
            
            # Verifica diretório do modelo
            if not self.model_dir.exists():
                raise FileNotFoundError(f"Diretório do modelo não encontrado: {self.model_dir}")
            
            # Carrega o modelo base
            self._load_base_model()
            
            logger.info(f"Fish Speech inicializado no dispositivo: {self.device}")
            
        except Exception as e:
            logger.error(f"Erro na inicialização do Fish Speech: {str(e)}")
            raise

    def _load_base_model(self) -> None:
        """Carrega o modelo base do Fish Speech."""
        try:
            # Caminhos dos arquivos
            model_path = self.model_dir / "model.pth"
            config_path = self.model_dir / "config.json"
            
            # Verifica arquivos
            if not model_path.exists():
                raise FileNotFoundError(f"Arquivo do modelo não encontrado: {model_path}")
            
            # Carrega configuração se existir
            if config_path.exists():
                with open(config_path, 'r') as f:
                    self.config = json.load(f)
                logger.info("Configuração do modelo carregada")
            else:
                logger.warning("Arquivo de configuração não encontrado, usando padrões")
                self.config = {}
            
            # Carrega modelo
            self.model = torch.jit.load(model_path, map_location=self.device)
            self.model.eval()
            
            # Otimizações para GPU
            if torch.cuda.is_available():
                self.model = self.model.cuda()
                if hasattr(self.model, 'half'):
                    self.model = self.model.half()
            
            logger.info("Modelo base Fish Speech carregado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao carregar modelo base: {str(e)}")
            raise RuntimeError(f"Falha ao inicializar modelo Fish Speech: {str(e)}")

    def _load_voice(self, voice_name: str) -> Optional[torch.Tensor]:
        """Carrega um modelo de voz específico."""
        if voice_name in self.loaded_voices:
            return self.loaded_voices[voice_name]

        try:
            # Procura primeiro nas vozes pré-treinadas
            voice_path = self.model_dir / "voices" / f"{voice_name}.pth"
            
            # Se não encontrar, procura nas vozes customizadas
            if not voice_path.exists():
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

    @torch.no_grad()
    def generate_speech(
        self,
        text: str,
        voice_name: str = "default",
        language: str = "pt-BR",
        output_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Gera áudio a partir de texto usando a voz especificada.
        
        Args:
            text: Texto para sintetizar
            voice_name: Nome da voz a ser usada
            language: Código do idioma
            output_path: Caminho para salvar o áudio
            
        Returns:
            Path do arquivo de áudio gerado ou None em caso de erro
        """
        try:
            # Validações
            if len(text) > self.max_text_length:
                raise ValueError(f"Texto muito longo. Máximo: {self.max_text_length} caracteres")
            
            # Carrega voz
            voice_model = self._load_voice(voice_name)
            if voice_model is None:
                raise ValueError(f"Voz {voice_name} não pôde ser carregada")
            
            # Gera áudio
            with torch.cuda.amp.autocast(enabled=torch.cuda.is_available()):
                waveform = self.model.forward(text, voice_model)
                
            # Define caminho de saída
            if output_path is None:
                temp_dir = Path(tempfile.gettempdir())
                output_path = str(temp_dir / f"tts_{uuid.uuid4()}.wav")
                
            # Salva áudio
            torchaudio.save(
                output_path,
                waveform.cpu(),
                self.sample_rate,
                format="wav"
            )
            
            # Limpa cache CUDA
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                
            logger.info(f"Áudio gerado com sucesso: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Erro na geração de áudio: {str(e)}")
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
