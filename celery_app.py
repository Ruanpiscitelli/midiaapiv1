"""
Configuração do Celery para processamento assíncrono.

Este módulo configura o Celery para:
- Processamento de imagens com SDXL
- Síntese de voz com Fish Speech
- Geração de vídeos com MoviePy
"""

import os
from celery import Celery
from config import CELERY_CONFIG

# Configura o Celery
app = Celery('midiaapiv1')

# Aplica configurações
app.conf.update(CELERY_CONFIG)

# Configura imports automáticos
app.autodiscover_tasks(['tasks'])

if __name__ == '__main__':
    app.start()
