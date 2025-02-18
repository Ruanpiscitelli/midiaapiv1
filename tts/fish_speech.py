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
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model = None
            self.tokenizer = None
            self.loaded_voices: Dict[str, torch.Tensor] = {}
            self.sample_rate = FISH_SPEECH_CONFIG["sample_rate"]
            self.max_text_length = FISH_SPEECH_CONFIG.get("max_text_length", 1000)
            self.batch_size = FISH_SPEECH_CONFIG.get("batch_size", 1)
            self.temperature = FISH_SPEECH_CONFIG.get("temperature", 0.8)
            
            # Carrega configurações do modelo
            self._load_config()
            
            # Carrega o modelo base
            self._load_base_model()
            
            # Carrega o tokenizer
            self._load_tokenizer()
            
            logger.info(f"Fish Speech inicializado no dispositivo: {self.device}")
            
        except Exception as e:
            logger.error(f"Erro na inicialização do Fish Speech: {str(e)}")
            raise

    def _load_config(self) -> None:
        """Carrega e valida configurações do modelo."""
        config_path = Path(FISH_SPEECH_CONFIG["model_path"]) / "config.json"
        if not config_path.exists():
            raise FileNotFoundError(f"Arquivo de configuração não encontrado: {config_path}")
            
        with open(config_path, 'r') as f:
            self.config = json.load(f)
            
        # Valida configurações essenciais
        required_keys = ["model_type", "vocab_size", "hidden_size"]
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Configuração ausente: {key}")

    def _load_base_model(self) -> None:
        """Carrega o modelo base do Fish Speech."""
        try:
            model_path = Path(FISH_SPEECH_CONFIG["model_path"]) / "model.pt"
            if not model_path.exists():
                raise FileNotFoundError(f"Modelo não encontrado: {model_path}")
                
            # Carrega modelo com tratamento de versão
            self.model = torch.jit.load(model_path, map_location=self.device)
            self.model.eval()
            
            # Verifica se o modelo tem os métodos necessários
            required_methods = ["encode_text", "generate_speech"]
            for method in required_methods:
                if not hasattr(self.model, method):
                    raise AttributeError(f"Modelo não possui método: {method}")
                    
            logger.info("Modelo base Fish Speech carregado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao carregar modelo base: {str(e)}")
            raise RuntimeError("Falha ao inicializar modelo Fish Speech")

    def _load_tokenizer(self) -> None:
        """Carrega o tokenizer do modelo."""
        try:
            tokenizer_path = Path(FISH_SPEECH_CONFIG["model_path"]) / "tokenizer.json"
            if not tokenizer_path.exists():
                raise FileNotFoundError(f"Tokenizer não encontrado: {tokenizer_path}")
                
            with open(tokenizer_path, 'r') as f:
                self.tokenizer = json.load(f)
                
            logger.info("Tokenizer carregado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao carregar tokenizer: {str(e)}")
            raise

    def _preprocess_text(self, text: str, language: str) -> torch.Tensor:
        """
        Prepara o texto para síntese.
        
        Args:
            text: Texto para sintetizar
            language: Código do idioma
            
        Returns:
            Tensor com os tokens do texto
        """
        if len(text) > self.max_text_length:
            raise ValueError(f"Texto muito longo. Máximo: {self.max_text_length} caracteres")
            
        # Tokeniza o texto
        tokens = self.model.encode_text(text, language)
        return tokens.to(self.device)

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
            if language not in FISH_SPEECH_CONFIG["supported_languages"]:
                raise ValueError(f"Idioma {language} não suportado")
                
            # Carrega voz
            voice_model = self._load_voice(voice_name)
            if voice_model is None:
                raise ValueError(f"Voz {voice_name} não pôde ser carregada")
                
            # Processa texto
            tokens = self._preprocess_text(text, language)
            
            # Gera áudio
            with torch.cuda.amp.autocast():
                waveform = self.model.generate_speech(
                    tokens,
                    voice_model,
                    temperature=self.temperature
                )
                
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

# Instância global
tts = FishSpeechTTS()
