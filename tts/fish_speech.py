"""
Módulo de síntese de voz usando Fish Speech.

Este módulo implementa a geração de voz sintética usando o modelo Fish Speech.
Suporta múltiplas vozes pré-treinadas e clonagem de voz a partir de amostras.

Documentação:
- O modelo base é carregado uma única vez e mantido em memória
- Vozes pré-treinadas são carregadas sob demanda
- Suporta clonagem de voz a partir de amostras de áudio
- Otimizado para GPU com processamento em batch quando possível
"""

import os
import torch
import torchaudio
import numpy as np
import logging
from pathlib import Path
from typing import Optional, Union, Dict
import tempfile
import uuid

from config import FISH_SPEECH_CONFIG
from storage.minio_client import upload_file

# Configuração de logging
logger = logging.getLogger(__name__)

class FishSpeechTTS:
    """Classe principal para síntese de voz usando Fish Speech."""
    
    def __init__(self):
        """Inicializa o modelo Fish Speech e carrega configurações."""
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.loaded_voices: Dict[str, torch.Tensor] = {}
        self.sample_rate = FISH_SPEECH_CONFIG["sample_rate"]
        
        # Carrega o modelo base
        self._load_base_model()
        logger.info(f"Fish Speech inicializado no dispositivo: {self.device}")

    def _load_base_model(self) -> None:
        """Carrega o modelo base do Fish Speech."""
        try:
            model_path = FISH_SPEECH_CONFIG["model_path"]
            self.model = torch.jit.load(model_path).to(self.device)
            self.model.eval()
            logger.info("Modelo base Fish Speech carregado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao carregar modelo base: {str(e)}")
            raise RuntimeError("Falha ao inicializar modelo Fish Speech")

    def _load_voice(self, voice_name: str) -> Optional[torch.Tensor]:
        """Carrega um modelo de voz específico."""
        if voice_name in self.loaded_voices:
            return self.loaded_voices[voice_name]

        try:
            # Procura primeiro nas vozes pré-treinadas
            voice_path = FISH_SPEECH_CONFIG["voice_dir"] / f"{voice_name}.pth"
            
            # Se não encontrar, procura nas vozes customizadas
            if not voice_path.exists():
                voice_path = FISH_SPEECH_CONFIG["custom_voice_dir"] / f"{voice_name}.pth"
            
            if not voice_path.exists():
                raise FileNotFoundError(f"Voz {voice_name} não encontrada")

            voice_model = torch.load(voice_path, map_location=self.device)
            self.loaded_voices[voice_name] = voice_model
            logger.info(f"Voz {voice_name} carregada com sucesso")
            return voice_model

        except Exception as e:
            logger.error(f"Erro ao carregar voz {voice_name}: {str(e)}")
            return None

    def _preprocess_text(self, text: str, language: str) -> torch.Tensor:
        """Prepara o texto para síntese."""
        # Aqui seria implementado o preprocessamento específico do Fish Speech
        # Por exemplo, normalização de texto, conversão de números, etc.
        # Retorna um tensor com os tokens do texto
        # Esta é uma implementação simplificada
        return torch.tensor([ord(c) for c in text], device=self.device)

    def clone_voice(self, audio_sample_path: str, voice_name: str) -> bool:
        """Clona uma voz a partir de uma amostra de áudio."""
        try:
            # Carrega e processa a amostra de áudio
            waveform, sample_rate = torchaudio.load(audio_sample_path)
            if sample_rate != self.sample_rate:
                waveform = torchaudio.transforms.Resample(sample_rate, self.sample_rate)(waveform)
            
            # Extrai características da voz (implementação específica do Fish Speech)
            voice_features = self._extract_voice_features(waveform)
            
            # Salva o modelo de voz clonada
            output_path = FISH_SPEECH_CONFIG["custom_voice_dir"] / f"{voice_name}.pth"
            torch.save(voice_features, output_path)
            
            # Carrega a voz recém-clonada
            self.loaded_voices[voice_name] = voice_features
            logger.info(f"Voz clonada com sucesso: {voice_name}")
            return True

        except Exception as e:
            logger.error(f"Erro ao clonar voz: {str(e)}")
            return False

    def _extract_voice_features(self, waveform: torch.Tensor) -> torch.Tensor:
        """Extrai características de voz de uma amostra de áudio."""
        # Implementação específica do Fish Speech para extração de características
        # Esta é uma implementação simplificada
        with torch.no_grad():
            features = self.model.extract_features(waveform.to(self.device))
        return features

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
            language: Código do idioma (ex: "pt-BR", "en-US")
            output_path: Caminho para salvar o áudio (opcional)
            
        Returns:
            Path do arquivo de áudio gerado ou None em caso de erro
        """
        try:
            # Verifica se o idioma é suportado
            if language not in FISH_SPEECH_CONFIG["supported_languages"]:
                raise ValueError(f"Idioma {language} não suportado")

            # Carrega a voz se necessário
            voice_model = self._load_voice(voice_name)
            if voice_model is None:
                raise ValueError(f"Voz {voice_name} não pôde ser carregada")

            # Prepara o texto
            text_tensor = self._preprocess_text(text, language)

            # Gera o áudio
            with torch.no_grad():
                waveform = self.model.generate(
                    text_tensor,
                    voice_model,
                    language=language
                )

            # Define o caminho de saída
            if output_path is None:
                temp_dir = Path(tempfile.gettempdir())
                output_path = str(temp_dir / f"tts_{uuid.uuid4()}.wav")

            # Salva o áudio
            torchaudio.save(
                output_path,
                waveform.cpu(),
                self.sample_rate,
                format="wav"
            )

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
        
        Args:
            text: Texto para sintetizar
            job_id: ID do job para identificação do arquivo
            voice_name: Nome da voz a ser usada
            language: Código do idioma
            
        Returns:
            URL do arquivo no MinIO ou None em caso de erro
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
            os.remove(audio_path)

            return url

        except Exception as e:
            logger.error(f"Erro no processo de geração e upload: {str(e)}")
            return None

# Instância global do TTS
tts = FishSpeechTTS()
