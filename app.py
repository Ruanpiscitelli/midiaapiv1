import os
import uuid
import logging.config
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from redis import asyncio as aioredis
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from tasks.tasks import generate_image_task, generate_tts_task, generate_video_task, clone_voice_task
from db.database import get_job_status, store_job, update_job_status
from storage.minio_client import get_presigned_url

# Importa configurações
from config import (
    LOGGING_CONFIG,
    CACHE_CONFIG,
    RATE_LIMIT_CONFIG,
    API_KEY
)

# Configura logging
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger("api")

# Configura rate limiting
RATE_LIMIT_ENABLED = RATE_LIMIT_CONFIG["enabled"]
if RATE_LIMIT_ENABLED:
    limiter = Limiter(key_func=get_remote_address)
else:
    limiter = None

# Inicializa a API FastAPI com metadados
app = FastAPI(
    title="Gerador de Vídeos com IA",
    description="""
    API para geração automática de vídeos utilizando Inteligência Artificial.
    
    ## Funcionalidades
    
    * 🖼️ Geração de imagens com Stable Diffusion XL
    * 🗣️ Síntese de voz com Fish Speech (com suporte a clonagem de voz)
    * 🎥 Composição de vídeos com MoviePy
    * 🔄 Processamento assíncrono via Celery
    
    ## Autenticação
    
    Todas as requisições requerem uma API Key válida no header `X-API-Key`.
    """,
    version="2.0",
    contact={
        "name": "Suporte",
        "email": "suporte@exemplo.com"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    }
)

# Configura rate limiting na aplicação
if limiter:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.on_event("startup")
async def startup():
    """Configura serviços no startup da aplicação."""
    # Configura Redis para cache
    redis = aioredis.from_url(
        CACHE_CONFIG["REDIS_URL"],
        encoding="utf8",
        decode_responses=True
    )
    
    # Inicializa cache
    FastAPICache.init(
        RedisBackend(redis),
        prefix=CACHE_CONFIG["CACHE_PREFIX"],
        key_builder=None,  # Usa key builder padrão
        enable=True
    )
    
    logger.info("Aplicação iniciada com sucesso")
    logger.info(f"Cache configurado: {CACHE_CONFIG['REDIS_URL']}")
    if limiter:
        logger.info("Rate limiting ativado")

@app.on_event("shutdown")
async def shutdown():
    """Executa limpeza no shutdown da aplicação."""
    logger.info("Aplicação finalizada")

# Middleware de autenticação
def authenticate_api_key(x_api_key: str = Header(..., description="API Key para autenticação")):
    """Verifica se a API Key fornecida é válida."""
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail={
                "message": "API Key inválida",
                "type": "authentication_error"
            }
        )
    return True

# Middleware para logging melhorado
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware para logging detalhado de requisições e respostas."""
    import time
    
    # Log da requisição
    start_time = time.time()
    method = request.method
    url = str(request.url)
    
    # Extrai informações adicionais
    client_host = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    # Log inicial detalhado
    logger.info(
        f"Request iniciada: {method} {url} - "
        f"Client: {client_host} - "
        f"User-Agent: {user_agent}"
    )
    
    try:
        # Processa a requisição
        response = await call_next(request)
        
        # Calcula tempo de processamento
        process_time = time.time() - start_time
        
        # Log da resposta com detalhes
        logger.info(
            f"Request completada: {method} {url} - "
            f"Status: {response.status_code} - "
            f"Tempo: {process_time:.2f}s - "
            f"Client: {client_host}"
        )
        
        return response
        
    except Exception as e:
        # Log de erro detalhado
        logger.error(
            f"Erro na request: {method} {url} - "
            f"Error: {str(e)} - "
            f"Client: {client_host}",
            exc_info=True
        )
        raise

# Função helper para logging de erros
def log_error(error: Exception, context: str = None):
    """Helper para logging padronizado de erros."""
    error_msg = f"Erro em {context}: {str(error)}" if context else str(error)
    logger.error(error_msg, exc_info=True)

# Enums para validação
class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"

class VideoResolution(str, Enum):
    sd = "sd"  # 854x480
    hd = "hd"  # 1280x720
    full_hd = "full-hd"  # 1920x1080

class VideoQuality(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"

# 🔹 Modelo para definir um elemento dentro de uma cena
class Element(BaseModel):
    type: str = Field(..., description="Tipo do elemento (video, image, text, etc.)")
    src: Optional[str] = Field(None, description="URL ou caminho do arquivo (para video, image, etc.)")
    text: Optional[str] = Field(None, description="Texto, se aplicável (para elementos text)")
    position: str = Field("center-center", description="Posição do elemento (ex: center-center, top-left)")
    width: int = Field(-1, description="Se -1, mantém a proporção original")
    height: int = Field(-1, description="Se -1, mantém a proporção original")
    duration: float = Field(-1, description="Duração do elemento; se -1, usa padrão (ex.: 5s)")
    volume: float = Field(1.0, description="Ajuste de volume (para áudio)", ge=0.0, le=2.0)

    class Config:
        schema_extra = {
            "example": {
                "type": "image",
                "src": "https://exemplo.com/imagem.jpg",
                "position": "center-center",
                "width": 1280,
                "height": 720,
                "duration": 5.0
            }
        }

# 🔹 Modelo para definir uma cena no vídeo
class Scene(BaseModel):
    """Modelo para uma cena do vídeo."""
    id: Optional[str] = Field(None, description="ID da cena (pode ser gerado automaticamente)")
    background_color: str = Field("#000000", description="Cor de fundo em hex")
    duration: float = Field(-1, description="Se -1, calcula automaticamente com base nos elementos")
    elements: List[dict] = Field(..., description="Elementos da cena")
    cache: bool = Field(True, description="Se deve cachear os elementos da cena")
    comment: Optional[str] = Field(None, description="Comentário opcional sobre a cena")

    class Config:
        schema_extra = {
            "example": {
                "id": "scene_1",
                "background_color": "#000000",
                "duration": 10.0,
                "elements": [
                    {
                        "type": "image",
                        "src": "https://exemplo.com/imagem.jpg",
                        "duration": 5.0
                    },
                    {
                        "type": "text",
                        "text": "Olá mundo!",
                        "position": "center-center"
                    }
                ],
                "cache": True,
                "comment": "Cena de abertura"
            }
        }

# 🔹 Modelo para requisição de geração de vídeo
class VideoRequest(BaseModel):
    comment: Optional[str] = Field("Meu Projeto", description="Comentário sobre o projeto")
    resolution: VideoResolution = Field(VideoResolution.full_hd, description="Resolução do vídeo")
    width: Optional[int] = Field(1920, description="Largura personalizada do vídeo")
    height: Optional[int] = Field(1080, description="Altura personalizada do vídeo")
    quality: VideoQuality = Field(VideoQuality.high, description="Qualidade do vídeo")
    cache: bool = Field(True, description="Se deve usar cache para otimização")
    draft: bool = Field(True, description="Se true, adiciona marca d'água")
    scenes: List[Scene] = Field(..., description="Lista de cenas que compõem o vídeo")

    class Config:
        schema_extra = {
            "example": {
                "comment": "Vídeo promocional",
                "resolution": "full-hd",
                "quality": "high",
                "scenes": [
                    {
                        "background_color": "#000000",
                        "elements": [
                            {
                                "type": "image",
                                "src": "https://exemplo.com/imagem.jpg"
                            }
                        ]
                    }
                ]
            }
        }

# 🔹 Modelo para requisição de geração de imagem
class ImageRequest(BaseModel):
    image_prompt: str = Field(..., description="Texto descritivo para geração da imagem", min_length=1, max_length=1000)
    width: int = Field(1280, description="Largura da imagem", ge=512, le=2048)
    height: int = Field(720, description="Altura da imagem", ge=512, le=2048)
    steps: int = Field(25, description="Número de passos de inferência", ge=10, le=50)
    seed: Optional[int] = Field(None, description="Seed para reprodutibilidade")

    class Config:
        schema_extra = {
            "example": {
                "image_prompt": "Uma paisagem de montanhas ao pôr-do-sol",
                "width": 1280,
                "height": 720,
                "steps": 25
            }
        }

# 🔹 Modelos para TTS
class VoiceCloneRequest(BaseModel):
    audio_sample_url: str = Field(..., description="URL do arquivo de áudio para clonagem de voz")
    voice_name: str = Field(..., description="Nome para identificar a voz clonada")
    description: Optional[str] = Field(None, description="Descrição opcional da voz")

    class Config:
        schema_extra = {
            "example": {
                "audio_sample_url": "https://exemplo.com/amostra.wav",
                "voice_name": "locutor_1",
                "description": "Voz masculina formal"
            }
        }

class TTSRequest(BaseModel):
    text: str = Field(..., description="Texto para sintetizar em voz", min_length=1, max_length=5000)
    language: str = Field("pt-BR", description="Código do idioma (ex: pt-BR, en-US)")
    voice: str = Field("default", description="Nome da voz a ser usada")
    voice_sample_url: Optional[str] = Field(None, description="URL de amostra para clonagem de voz on-the-fly")
    speed: float = Field(1.0, description="Velocidade da fala", ge=0.5, le=2.0)
    pitch: float = Field(1.0, description="Tom da voz", ge=0.5, le=2.0)
    volume: float = Field(1.0, description="Volume da voz", ge=0.0, le=2.0)

    class Config:
        schema_extra = {
            "example": {
                "text": "Olá, bem-vindo ao nosso vídeo!",
                "language": "pt-BR",
                "voice": "male_1",
                "speed": 1.0
            }
        }

class TTSResponse(BaseModel):
    job_id: str = Field(..., description="ID único do job")
    status: JobStatus = Field(..., description="Status atual do job")
    voice_used: str = Field(..., description="Nome da voz utilizada")
    estimated_duration: Optional[float] = Field(None, description="Duração estimada do áudio em segundos")

# 🔹 Modelos para respostas da API
class JobResponse(BaseModel):
    job_id: str = Field(..., description="ID único do job")
    status: JobStatus = Field(..., description="Status atual do job")
    created_at: Optional[str] = Field(None, description="Data/hora de criação do job")
    updated_at: Optional[str] = Field(None, description="Data/hora da última atualização")

class JobStatusResponse(JobResponse):
    progress: Optional[Dict[str, Any]] = Field(None, description="Informações de progresso do job")
    error_message: Optional[str] = Field(None, description="Mensagem de erro em caso de falha")
    result: Optional[Dict[str, Any]] = Field(None, description="Resultado do job quando concluído")

class JobResultResponse(BaseModel):
    job_id: str = Field(..., description="ID único do job")
    result_url: str = Field(..., description="URL para download do resultado")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadados adicionais")
    files: Optional[Dict[str, List[str]]] = Field(None, description="URLs de arquivos auxiliares")

class HealthCheckResponse(BaseModel):
    """Modelo para resposta do health check."""
    status: str
    version: str
    uptime: float
    database_status: str
    redis_status: str 
    minio_status: str

# ✅ Endpoint para criar um novo vídeo
@app.post(
    "/generate-video",
    response_model=JobResponse,
    status_code=202,
    tags=["Vídeo"],
    dependencies=[Depends(authenticate_api_key)]
)
@limiter.limit(RATE_LIMIT_CONFIG["generate_video"]) if limiter else None
async def generate_video(request: VideoRequest, x_api_key: str = Depends(authenticate_api_key)):
    """Inicia a geração assíncrona de um vídeo."""
    try:
        job_id = str(uuid.uuid4())
        logger.info(f"Iniciando geração de vídeo - Job ID: {job_id}")
        
        store_job(job_id, "queued", request.dict())
        generate_video_task.delay(job_id, request.dict())
        
        logger.info(f"Job de vídeo enfileirado com sucesso - Job ID: {job_id}")
        return JobResponse(job_id=job_id, status=JobStatus.queued)
        
    except Exception as e:
        log_error(e, "generate_video")
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Erro ao iniciar geração do vídeo: {str(e)}",
                "type": "processing_error"
            }
        )

# ✅ Endpoint para verificar o status de um job (melhorado)
@app.get(
    "/status/{job_id}",
    response_model=JobStatusResponse,
    tags=["Jobs"],
    summary="Consulta o status de um job",
    dependencies=[Depends(authenticate_api_key)]
)
@limiter.limit(RATE_LIMIT_CONFIG["status"]) if limiter else None
@cache(expire=CACHE_CONFIG["CACHE_TIMES"]["status"])
async def get_job_status_endpoint(job_id: str, x_api_key: str = Depends(authenticate_api_key)):
    """Retorna o status atual de um job."""
    try:
        logger.info(f"Consultando status do job: {job_id}")
        status = get_job_status(job_id)
        
        if not status:
            logger.warning(f"Job não encontrado: {job_id}")
            raise HTTPException(
                status_code=404,
                detail={
                    "message": f"Job {job_id} não encontrado",
                    "type": "not_found"
                }
            )
            
        logger.info(f"Status do job {job_id}: {status['status']}")
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, f"get_job_status - Job ID: {job_id}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Erro ao consultar status: {str(e)}",
                "type": "processing_error"
            }
        )

# ✅ Endpoint para obter o resultado do job (melhorado)
@app.get(
    "/result/{job_id}",
    response_model=JobResultResponse,
    tags=["Jobs"],
    summary="Obtém o resultado de um job concluído",
    dependencies=[Depends(authenticate_api_key)]
)
async def get_job_result(job_id: str):
    """Retorna o resultado de um job concluído."""
    try:
        status = get_job_status(job_id)
        if not status:
            raise HTTPException(
                status_code=404,
                detail={
                    "message": f"Job {job_id} não encontrado",
                    "type": "not_found"
                }
            )
            
        if status["status"] != JobStatus.completed:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": f"Job {job_id} ainda não foi concluído",
                    "type": "job_not_completed",
                    "current_status": status["status"]
                }
            )
            
        # Gera URLs pré-assinadas para os arquivos
        result_url = get_presigned_url(f"videos/{job_id}.mp4")
        
        # Opcionalmente, gera URLs para arquivos auxiliares
        files = {}
        if "images" in status.get("result", {}):
            files["images"] = [
                get_presigned_url(f"images/{img_id}.png")
                for img_id in status["result"]["images"]
            ]
            
        if "audios" in status.get("result", {}):
            files["audios"] = [
                get_presigned_url(f"audios/{audio_id}.wav")
                for audio_id in status["result"]["audios"]
            ]
            
        return JobResultResponse(
            job_id=job_id,
            result_url=result_url,
            metadata=status.get("result", {}).get("metadata"),
            files=files
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Erro ao obter resultado: {str(e)}",
                "type": "processing_error"
            }
        )

# ✅ Endpoint para geração de imagem
@app.post(
    "/generate-image",
    response_model=JobResponse,
    status_code=202,
    tags=["Imagem"],
    summary="Gera uma imagem com Stable Diffusion XL",
    dependencies=[Depends(authenticate_api_key)]
)
async def generate_image(request: ImageRequest):
    """Inicia a geração assíncrona de uma imagem."""
    try:
        job_id = str(uuid.uuid4())
        store_job(job_id, "queued", request.dict())
        generate_image_task.delay(job_id, request.dict())
        
        return JobResponse(
            job_id=job_id,
            status=JobStatus.queued
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Erro ao iniciar geração da imagem: {str(e)}",
                "type": "processing_error"
            }
        )

# ✅ Endpoint para clonagem de voz
@app.post(
    "/clone-voice",
    response_model=TTSResponse,
    tags=["Voz"],
    summary="Clona uma voz a partir de uma amostra de áudio",
    description="""
    Inicia o processo de clonagem de voz a partir de uma amostra de áudio.
    A voz clonada pode ser usada posteriormente para síntese de fala.
    """
)
async def clone_voice(
    request: VoiceCloneRequest,
    x_api_key: str = Depends(authenticate_api_key)
):
    """
    Clona uma voz a partir de uma amostra de áudio.
    
    Args:
        request: Dados para clonagem de voz
        x_api_key: Chave de API para autenticação
        
    Returns:
        TTSResponse com detalhes do job de clonagem
    """
    job_id = str(uuid.uuid4())
    store_job(job_id, "queued")
    
    # Dispara tarefa assíncrona para clonar a voz
    clone_voice_task.delay(job_id, request.dict())
    
    return {
        "job_id": job_id,
        "status": "queued",
        "voice_used": request.voice_name,
        "estimated_duration": None
    }

# ✅ Endpoint para geração de áudio (TTS)
@app.post(
    "/generate-tts",
    response_model=TTSResponse,
    status_code=202,
    tags=["Áudio"],
    summary="Gera áudio a partir de texto",
    dependencies=[Depends(authenticate_api_key)]
)
async def generate_tts(request: TTSRequest):
    """Inicia a geração assíncrona de áudio TTS."""
    try:
        job_id = str(uuid.uuid4())
        store_job(job_id, "queued", request.dict())
        
        # Estima duração baseado no número de palavras
        words = len(request.text.split())
        estimated_duration = (words / 150) * 60  # ~150 palavras por minuto
        
        # Se tem URL de amostra, primeiro clona a voz
        if request.voice_sample_url:
            clone_voice_task.delay(job_id, request.voice_sample_url)
            
        generate_tts_task.delay(job_id, request.dict())
        
        return TTSResponse(
            job_id=job_id,
            status=JobStatus.queued,
            voice_used=request.voice,
            estimated_duration=estimated_duration
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Erro ao iniciar geração do áudio: {str(e)}",
                "type": "processing_error"
            }
        )

# ✅ Endpoint para listar vozes disponíveis
@app.get(
    "/available-voices",
    tags=["Voz"],
    summary="Lista vozes disponíveis",
    description="Retorna uma lista de todas as vozes disponíveis para síntese de fala."
)
@limiter.limit(RATE_LIMIT_CONFIG["voices"]) if limiter else None
@cache(expire=CACHE_CONFIG["CACHE_TIMES"]["voices"])
async def list_voices(
    x_api_key: str = Depends(authenticate_api_key)
):
    """
    Lista todas as vozes disponíveis no sistema.
    
    Args:
        x_api_key: Chave de API para autenticação
        
    Returns:
        Lista de vozes disponíveis com seus metadados
    """
    # Obtém vozes do config
    from config import FISH_SPEECH_CONFIG
    
    # Lista vozes padrão e personalizadas
    voices = {
        "default_voices": [
            {
                "id": voice,
                "type": "predefined",
                "language": ["pt-BR", "en-US"],
                "gender": voice.split("_")[0]
            }
            for voice in FISH_SPEECH_CONFIG["available_voices"]
        ],
        "custom_voices": []  # Aqui você pode adicionar vozes clonadas do usuário
    }
    
    return voices

# ✅ Endpoint para consulta de status dos vídeos vinculados a um projeto
@app.get("/movies")
async def get_movies_status(project_id: str, x_api_key: str = Depends(authenticate_api_key)):
    # Exemplo fixo; em produção, consultar o banco para retornar os vídeos vinculados ao project_id
    return {
        "project_id": project_id,
        "movies": [
            {"id": "abc123", "status": "completed", "video_url": "https://meuminio.com/videos/abc123.mp4"},
            {"id": "def456", "status": "processing"}
        ]
    }

# ✅ Endpoint de health check (melhorado)
@app.get(
    "/health",
    response_model=HealthCheckResponse,
    tags=["Sistema"],
    summary="Verifica o status do sistema"
)
@limiter.limit(RATE_LIMIT_CONFIG["health"]) if limiter else None
@cache(expire=CACHE_CONFIG["CACHE_TIMES"]["health"])
async def health_check():
    """Retorna o status geral do sistema e suas dependências."""
    from datetime import datetime
    import psutil
    import redis
    from minio import Minio
    
    start_time = getattr(app, "start_time", datetime.now())
    uptime = (datetime.now() - start_time).total_seconds()
    
    # Verifica conexão com Redis
    redis_status = "ok"
    try:
        redis_client = redis.from_url(os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"))
        redis_client.ping()
    except:
        redis_status = "error"
        
    # Verifica conexão com MinIO
    minio_status = "ok"
    try:
        minio_client = Minio(
            os.getenv("MINIO_ENDPOINT", "localhost:9000"),
            access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
            secure=False
        )
        minio_client.list_buckets()
    except:
        minio_status = "error"
        
    # Verifica conexão com banco
    db_status = "ok"
    try:
        get_job_status("test")
    except:
        db_status = "error"
        
    return HealthCheckResponse(
        status="online",
        version="2.0",
        uptime=uptime,
        database_status=db_status,
        redis_status=redis_status,
        minio_status=minio_status
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
