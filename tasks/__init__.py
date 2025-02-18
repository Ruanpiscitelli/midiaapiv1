"""
Pacote de tarefas assíncronas usando Celery.
Este pacote contém todas as tarefas que são executadas em background.

Documentação:
- Tarefas de geração de imagem via Stable Diffusion XL
- Tarefas de síntese de voz via Fish Speech
- Tarefas de composição de vídeo via MoviePy
- Integração com MinIO para armazenamento
"""

from .tasks import (
    generate_image_task,
    generate_tts_task,
    generate_video_task
)

# Exporta as tarefas principais para uso direto
# Exemplo de uso:
# from tasks import generate_video_task
# job = generate_video_task.delay(job_id, request_data)
