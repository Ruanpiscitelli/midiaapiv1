"""
Módulo de edição e composição de vídeos usando MoviePy.

Este módulo é responsável por:
- Combinar imagens e áudios em vídeos
- Renderizar vídeos com diferentes resoluções e qualidades
- Aplicar efeitos de transição entre cenas
- Sincronizar áudio com imagens
"""

import os
import uuid
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger
from moviepy.editor import (
    ImageClip,
    AudioFileClip,
    CompositeVideoClip,
    concatenate_videoclips,
    VideoFileClip,
    TextClip
)
from config import VIDEO_CONFIG
from storage.minio_client import upload_file

def create_video_from_scenes(job_id: str, scenes: List[Dict[str, Any]]) -> Optional[str]:
    """
    Cria um vídeo a partir de uma lista de cenas.
    
    Args:
        job_id: ID único do job
        scenes: Lista de cenas, cada uma com imagens, áudios e configurações
        
    Returns:
        URL do vídeo no MinIO ou None em caso de erro
        
    Cada cena deve ter:
    - background_color: Cor de fundo (ex: "#000000")
    - duration: Duração em segundos (-1 para automático)
    - elements: Lista de elementos (imagens, áudios, textos)
    """
    try:
        logger.info(f"Iniciando criação de vídeo para job {job_id}")
        
        # Cria diretório temporário para arquivos
        temp_dir = Path(tempfile.mkdtemp())
        output_path = temp_dir / f"{job_id}.mp4"
        
        # Lista para armazenar os clips de cada cena
        video_clips = []
        
        # Processa cada cena
        for i, scene in enumerate(scenes):
            logger.info(f"Processando cena {i+1}/{len(scenes)}")
            
            # Cria clip da cena
            scene_clip = render_scene(
                scene,
                width=VIDEO_CONFIG["default_resolution"]["width"],
                height=VIDEO_CONFIG["default_resolution"]["height"]
            )
            
            if scene_clip:
                video_clips.append(scene_clip)
        
        if not video_clips:
            raise ValueError("Nenhuma cena válida para processar")
        
        # Concatena todas as cenas
        final_video = concatenate_videoclips(video_clips, method="compose")
        
        # Configura codec e qualidade
        write_videofile_kwargs = {
            "fps": VIDEO_CONFIG["fps"],
            "codec": VIDEO_CONFIG["codec"],
            "audio_codec": VIDEO_CONFIG["audio_codec"],
            "bitrate": VIDEO_CONFIG["bitrate"],
            "threads": 2,  # Usar mais threads para renderização mais rápida
            "logger": None  # Evita logs excessivos do MoviePy
        }
        
        # Renderiza o vídeo final
        final_video.write_videofile(
            str(output_path),
            **write_videofile_kwargs
        )
        
        # Faz upload para o MinIO
        object_name = f"videos/{job_id}.mp4"
        video_url = upload_file(str(output_path), object_name)
        
        # Limpa arquivos temporários
        for clip in video_clips:
            clip.close()
        final_video.close()
        
        if os.path.exists(output_path):
            os.remove(output_path)
            
        return video_url
        
    except Exception as e:
        logger.error(f"Erro ao criar vídeo: {str(e)}")
        return None

def render_scene(
    scene: Dict[str, Any],
    width: int = 1280,
    height: int = 720
) -> Optional[CompositeVideoClip]:
    """
    Renderiza uma cena individual do vídeo.
    
    Args:
        scene: Dicionário com configurações da cena
        width: Largura do vídeo
        height: Altura do vídeo
        
    Returns:
        Clip da cena renderizada ou None em caso de erro
    """
    try:
        # Lista para armazenar elementos da cena
        scene_elements = []
        
        # Duração total da cena (será ajustada com base nos elementos)
        scene_duration = scene.get("duration", -1)
        
        # Processa cada elemento da cena
        for element in scene["elements"]:
            element_clip = None
            
            if element["type"] == "image":
                # Carrega imagem
                element_clip = ImageClip(element["src"])
                
                # Ajusta tamanho mantendo proporção
                if element["width"] != -1 and element["height"] != -1:
                    element_clip = element_clip.resize(
                        width=element["width"],
                        height=element["height"]
                    )
                
            elif element["type"] == "audio":
                # Carrega áudio
                audio_clip = AudioFileClip(element["src"])
                
                # Ajusta volume se especificado
                if "volume" in element and element["volume"] != 1.0:
                    audio_clip = audio_clip.volumex(element["volume"])
                
                # Se não houver duração definida, usa a do áudio
                if scene_duration == -1:
                    scene_duration = audio_clip.duration
                
                # Adiciona o áudio à cena
                if element_clip:
                    element_clip = element_clip.set_audio(audio_clip)
                else:
                    element_clip = CompositeVideoClip(
                        [ImageClip(color=scene["background_color"], duration=audio_clip.duration)],
                        size=(width, height)
                    ).set_audio(audio_clip)
            
            elif element["type"] == "text":
                # Cria texto
                text_clip = TextClip(
                    element["text"],
                    fontsize=element.get("font_size", 30),
                    color=element.get("color", "white"),
                    bg_color=element.get("bg_color", None),
                    font=element.get("font", "Arial")
                )
                
                # Posiciona o texto
                position = element.get("position", "center")
                if isinstance(position, str):
                    text_clip = text_clip.set_position(position)
                else:
                    text_clip = text_clip.set_position((position[0], position[1]))
                
                element_clip = text_clip
            
            # Define duração do elemento se especificada
            if element["duration"] != -1:
                element_clip = element_clip.set_duration(element["duration"])
            elif scene_duration != -1:
                element_clip = element_clip.set_duration(scene_duration)
            
            if element_clip:
                scene_elements.append(element_clip)
        
        # Cria o clip final da cena
        if scene_elements:
            scene_clip = CompositeVideoClip(
                scene_elements,
                size=(width, height),
                bg_color=scene.get("background_color", "#000000")
            )
            
            # Define duração final
            if scene_duration != -1:
                scene_clip = scene_clip.set_duration(scene_duration)
                
            return scene_clip
            
        return None
        
    except Exception as e:
        logger.error(f"Erro ao renderizar cena: {str(e)}")
        return None
