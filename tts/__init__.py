"""
Pacote de síntese de voz (TTS - Text to Speech).
Este pacote contém a implementação do sistema TTS usando Fish Speech.
"""

from .fish_speech import tts

# Exporta a instância global do TTS para uso direto
# Exemplo de uso:
# from tts import tts
# audio_path = tts.generate_speech("Olá mundo")
