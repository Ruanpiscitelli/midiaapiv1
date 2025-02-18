"""
Tarefas assíncronas do Celery.
Este módulo contém todas as tarefas que são executadas em background.

Documentação:
- Tarefas de geração de imagem via Stable Diffusion XL
- Tarefas de síntese de voz via Fish Speech
- Tarefas de composição de vídeo via MoviePy
- Integração com MinIO para armazenamento
"""

import uuid
import logging
from celery_app import app  # Importa a instância do Celery já configurada
from stable_diffusion.sdxl_model import generate_image
from tts.fish_speech import generate_tts
from video.editor import create_video_from_scenes
from storage.minio_client import upload_file
from db.database import update_job_status

# Configuração de logging
logger = logging.getLogger(__name__)

@app.task(bind=True, name='tasks.generate_image_task')
def generate_image_task(self, job_id, request_data):
    """ Tarefa assíncrona para gerar uma imagem usando Stable Diffusion XL """
    try:
        logger.info(f"Iniciando geração de imagem para job {job_id}")
        image_path = generate_image(
            prompt=request_data["image_prompt"],
            width=request_data.get("width", 1280),
            height=request_data.get("height", 720),
            steps=request_data.get("steps", 25),
            seed=request_data.get("seed", None)
        )

        # Faz upload da imagem para o MinIO
        image_url = upload_file(image_path, f"images/{job_id}.png")

        # Atualiza o status do job no banco de dados
        update_job_status(job_id, "completed", image_url)
        logger.info(f"Imagem gerada com sucesso para job {job_id}")
        return {"job_id": job_id, "image_url": image_url}

    except Exception as e:
        logger.error(f"Erro na geração de imagem para job {job_id}: {str(e)}")
        update_job_status(job_id, "failed", str(e))
        raise

@app.task(bind=True, name='tasks.generate_tts_task')
def generate_tts_task(self, job_id, request_data):
    """ Tarefa assíncrona para gerar um áudio usando Fish Speech """
    try:
        logger.info(f"Iniciando geração de áudio para job {job_id}")
        audio_path = generate_tts(
            text=request_data["text"],
            language=request_data.get("language", "pt"),
            voice=request_data.get("voice", "default")
        )

        # Faz upload do áudio para o MinIO
        audio_url = upload_file(audio_path, f"audios/{job_id}.wav")

        # Atualiza o status do job no banco de dados
        update_job_status(job_id, "completed", audio_url)
        logger.info(f"Áudio gerado com sucesso para job {job_id}")
        return {"job_id": job_id, "audio_url": audio_url}

    except Exception as e:
        logger.error(f"Erro na geração de áudio para job {job_id}: {str(e)}")
        update_job_status(job_id, "failed", str(e))
        raise

@app.task(bind=True, name='tasks.generate_video_task')
def generate_video_task(self, job_id, request_data):
    """ Tarefa assíncrona para gerar um vídeo a partir de cenas definidas pelo usuário """
    try:
        logger.info(f"Iniciando geração de vídeo para job {job_id}")
        video_url = create_video_from_scenes(job_id, request_data["scenes"])

        # Atualiza o status do job no banco de dados
        update_job_status(job_id, "completed", video_url)
        logger.info(f"Vídeo gerado com sucesso para job {job_id}")
        return {"job_id": job_id, "video_url": video_url}

    except Exception as e:
        logger.error(f"Erro na geração de vídeo para job {job_id}: {str(e)}")
        update_job_status(job_id, "failed", str(e))
        raise

@app.task(bind=True, name='tasks.clone_voice_task')
def clone_voice_task(self, job_id: str, request_data: dict):
    """Tarefa assíncrona para clonar uma voz a partir de uma amostra de áudio"""
    try:
        logger.info(f"Iniciando clonagem de voz para job {job_id}")
        
        # Atualiza status para processando
        update_job_status(job_id, "processing")
        
        # Clona a voz usando o Fish Speech
        success = tts.clone_voice(
            audio_sample_path=request_data["audio_sample_url"],
            voice_name=request_data["voice_name"]
        )
        
        if not success:
            raise RuntimeError("Falha na clonagem de voz")
        
        # Atualiza o status do job no banco de dados
        update_job_status(job_id, "completed", metadata={
            "voice_name": request_data["voice_name"],
            "description": request_data.get("description")
        })
        logger.info(f"Voz clonada com sucesso para job {job_id}")
        return {"job_id": job_id, "voice_name": request_data["voice_name"]}
        
    except Exception as e:
        logger.error(f"Erro na clonagem de voz para job {job_id}: {str(e)}")
        update_job_status(job_id, "failed", error_message=str(e))
        raise
