"""
Módulo de geração de imagens usando Stable Diffusion XL.

Este módulo é responsável por:
- Carregar e gerenciar o modelo SDXL
- Gerar imagens de alta qualidade
- Processar múltiplas imagens em batch
- Otimizar uso de memória GPU
- Limpar arquivos temporários
"""

import os
import gc
import uuid
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple
from loguru import logger
import torch
from torch import autocast
from diffusers import (
    StableDiffusionXLPipeline,
    DPMSolverMultistepScheduler,
    DiffusionPipeline,
    AutoencoderKL
)
from PIL import Image
import numpy as np

from config import SDXL_CONFIG, SDXL_MODEL_PATH, DEVICE
from storage import upload_file, get_presigned_url

class SDXLModel:
    """Classe para gerenciar o modelo Stable Diffusion XL."""
    
    def __init__(self):
        """Inicializa o modelo SDXL com configurações otimizadas."""
        try:
            logger.info("Iniciando inicialização do modelo SDXL...")
            self.device = DEVICE
            logger.info(f"Usando dispositivo: {self.device}")
            
            self.pipe = None
            self.temp_dir = Path(tempfile.mkdtemp())
            logger.info(f"Diretório temporário criado: {self.temp_dir}")
            
            # Configurações do modelo
            self.width = SDXL_CONFIG["width"]
            self.height = SDXL_CONFIG["height"]
            self.steps = SDXL_CONFIG["num_inference_steps"]
            self.guidance_scale = SDXL_CONFIG["guidance_scale"]
            self.negative_prompt = SDXL_CONFIG["negative_prompt"]
            
            # Carrega o modelo
            self._load_model()
            logger.info(f"SDXL inicializado no dispositivo: {self.device}")
        except Exception as e:
            logger.error(f"Erro na inicialização do SDXL: {str(e)}")
            raise

    def _load_model(self) -> None:
        """Carrega o modelo SDXL com otimizações."""
        try:
            logger.info("Iniciando carregamento do modelo SDXL...")
            
            # Converte PosixPath para string se necessário
            model_path = str(SDXL_MODEL_PATH) if isinstance(SDXL_MODEL_PATH, Path) else SDXL_MODEL_PATH
            
            # Carrega o modelo
            self.pipe = DiffusionPipeline.from_pretrained(
                model_path,
                torch_dtype=torch.float16,
                use_safetensors=True,
                variant="fp16"
            )

            # Move para GPU se disponível
            if torch.cuda.is_available():
                logger.info("Movendo modelo para GPU...")
                self.pipe = self.pipe.to(self.device)
                
                # Habilita otimizações
                if hasattr(self.pipe, 'enable_xformers_memory_efficient_attention'):
                    self.pipe.enable_xformers_memory_efficient_attention()
                
                # Habilita otimização de memória
                if hasattr(self.pipe, 'enable_model_cpu_offload'):
                    self.pipe.enable_model_cpu_offload()

            logger.info("Modelo SDXL carregado com sucesso!")
            
        except Exception as e:
            logger.error(f"Erro ao carregar modelo SDXL: {str(e)}")
            raise RuntimeError(f"Falha ao inicializar modelo SDXL: {str(e)}")

    def generate_image(
        self,
        prompt: str,
        seed: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        steps: Optional[int] = None
    ) -> Optional[str]:
        """
        Gera uma única imagem a partir de um prompt.
        
        Args:
            prompt: Texto descritivo para geração da imagem
            seed: Seed para reprodutibilidade (opcional)
            width: Largura personalizada (opcional)
            height: Altura personalizada (opcional)
            steps: Número de passos de inferência (opcional)
            
        Returns:
            Caminho do arquivo de imagem gerado ou None em caso de erro
        """
        try:
            return self.batch_generate_images(
                prompts=[prompt],
                seeds=[seed] if seed is not None else None,
                width=width,
                height=height,
                steps=steps
            )[0]
            
        except Exception as e:
            logger.error(f"Erro ao gerar imagem: {str(e)}")
            return None

    def batch_generate_images(
        self,
        prompts: List[str],
        seeds: Optional[List[int]] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        steps: Optional[int] = None,
        batch_size: int = 4
    ) -> List[str]:
        """
        Gera múltiplas imagens em batch para otimizar uso da GPU.
        
        Args:
            prompts: Lista de prompts para geração
            seeds: Lista de seeds para reprodutibilidade (opcional)
            width: Largura personalizada (opcional)
            height: Altura personalizada (opcional)
            steps: Número de passos de inferência (opcional)
            batch_size: Tamanho do batch para processamento
            
        Returns:
            Lista de caminhos dos arquivos de imagem gerados
            
        Raises:
            ValueError: Se os parâmetros forem inválidos
        """
        try:
            # Validações de entrada
            if not prompts:
                raise ValueError("Lista de prompts não pode estar vazia")
            
            if any(not isinstance(p, str) or not p.strip() for p in prompts):
                raise ValueError("Todos os prompts devem ser strings não vazias")
                
            if seeds is not None and any(not isinstance(s, int) for s in seeds if s is not None):
                raise ValueError("Seeds devem ser números inteiros")
                
            if width is not None and (not isinstance(width, int) or width < 256 or width > 2048):
                raise ValueError("Largura deve ser um inteiro entre 256 e 2048")
                
            if height is not None and (not isinstance(height, int) or height < 256 or height > 2048):
                raise ValueError("Altura deve ser um inteiro entre 256 e 2048")
                
            if steps is not None and (not isinstance(steps, int) or steps < 1 or steps > 150):
                raise ValueError("Número de passos deve ser um inteiro entre 1 e 150")
                
            if not isinstance(batch_size, int) or batch_size < 1:
                raise ValueError("Tamanho do batch deve ser um inteiro positivo")
            
            # Usa valores padrão se não especificados
            width = width or self.width
            height = height or self.height
            steps = steps or self.steps
            
            # Prepara seeds se não fornecidas
            if seeds is None:
                seeds = [None] * len(prompts)
            elif len(seeds) != len(prompts):
                raise ValueError("Número de seeds deve ser igual ao número de prompts")
            
            # Lista para armazenar resultados
            image_paths = []
            
            # Processa em batches
            for i in range(0, len(prompts), batch_size):
                batch_prompts = prompts[i:i + batch_size]
                batch_seeds = seeds[i:i + batch_size]
                
                # Gera imagens do batch
                batch_images = self._generate_batch(
                    prompts=batch_prompts,
                    seeds=batch_seeds,
                    width=width,
                    height=height,
                    steps=steps
                )
                
                # Salva imagens geradas
                for j, image in enumerate(batch_images):
                    image_path = self.temp_dir / f"{uuid.uuid4()}.png"
                    image.save(image_path, format="PNG", quality=95)
                    image_paths.append(str(image_path))
                
                # Limpa memória GPU
                torch.cuda.empty_cache()
                gc.collect()
            
            return image_paths
            
        except Exception as e:
            logger.error(f"Erro no batch de imagens: {str(e)}")
            self._cleanup_temp_files()
            raise
        
    def _generate_batch(
        self,
        prompts: List[str],
        seeds: List[Optional[int]],
        width: int,
        height: int,
        steps: int
    ) -> List[Image.Image]:
        """
        Gera um batch de imagens usando o modelo SDXL.
        
        Args:
            prompts: Lista de prompts para o batch
            seeds: Lista de seeds para o batch
            width: Largura das imagens
            height: Altura das imagens
            steps: Número de passos de inferência
            
        Returns:
            Lista de imagens PIL geradas
            
        Raises:
            RuntimeError: Se houver erro na geração das imagens
            ValueError: Se os parâmetros forem inválidos
            torch.cuda.OutOfMemoryError: Se não houver memória GPU suficiente
        """
        if not self.pipe:
            raise RuntimeError("Modelo não foi inicializado corretamente")
            
        try:
            # Configura gerador para seeds
            if any(seed is not None for seed in seeds):
                generators = [
                    torch.Generator(device=self.device).manual_seed(seed)
                    if seed is not None
                    else None
                    for seed in seeds
                ]
            else:
                generators = None
            
            # Gera imagens com autocast para otimizar memória
            try:
                with autocast(self.device.type):
                    output = self.pipe(
                        prompt=prompts,
                        negative_prompt=[self.negative_prompt] * len(prompts),
                        width=width,
                        height=height,
                        num_inference_steps=steps,
                        guidance_scale=self.guidance_scale,
                        generator=generators,
                        num_images_per_prompt=1
                    )
            except torch.cuda.OutOfMemoryError as e:
                logger.error("Memória GPU insuficiente. Tentando liberar cache...")
                torch.cuda.empty_cache()
                gc.collect()
                raise RuntimeError(f"Erro de memória GPU: {str(e)}. Tente reduzir o tamanho do batch ou da imagem.")
            except Exception as e:
                raise RuntimeError(f"Erro na geração das imagens: {str(e)}")
            
            if not output.images:
                raise RuntimeError("Nenhuma imagem foi gerada pelo modelo")
                
            return output.images
            
        except Exception as e:
            logger.error(f"Erro no _generate_batch: {str(e)}")
            raise

    def generate_and_upload(
        self,
        prompt: str,
        job_id: str,
        **kwargs
    ) -> Optional[str]:
        """
        Gera uma imagem e faz upload para o MinIO.
        
        Args:
            prompt: Texto descritivo para geração
            job_id: ID do job para identificação
            **kwargs: Argumentos adicionais para generate_image
            
        Returns:
            URL da imagem no MinIO ou None em caso de erro
        """
        try:
            # Gera a imagem
            image_path = self.generate_image(prompt, **kwargs)
            if image_path is None:
                raise RuntimeError("Falha na geração da imagem")
            
            # Faz upload para o MinIO
            object_name = f"images/{job_id}.png"
            url = upload_file(image_path, object_name)
            
            # Limpa arquivo temporário
            if os.path.exists(image_path):
                os.remove(image_path)
            
            return url
            
        except Exception as e:
            logger.error(f"Erro no processo de geração e upload: {str(e)}")
            return None
        
    def _cleanup_temp_files(self) -> None:
        """Limpa arquivos temporários."""
        try:
            if hasattr(self, 'temp_dir') and self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(str(self.temp_dir))
                self.temp_dir = Path(tempfile.mkdtemp())
                logger.info(f"Diretório temporário limpo e recriado: {self.temp_dir}")
        except Exception as e:
            logger.error(f"Erro ao limpar arquivos temporários: {str(e)}")
            # Não re-raise a exceção para evitar quebrar o fluxo principal

    def __del__(self):
        """Destrutor para limpeza de recursos."""
        try:
            self._cleanup_temp_files()
            if hasattr(self, 'pipe') and self.pipe is not None:
                del self.pipe
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    gc.collect()
                logger.info("Recursos do modelo SDXL liberados com sucesso")
        except Exception as e:
            logger.error(f"Erro ao liberar recursos do modelo: {str(e)}")

# Instância global do modelo
model = SDXLModel()

# Funções de interface para o módulo
def generate_image(prompt: str, **kwargs) -> Optional[str]:
    """Interface para geração de uma única imagem."""
    return model.generate_image(prompt, **kwargs)

def batch_generate_images(prompts: List[str], **kwargs) -> List[str]:
    """Interface para geração de múltiplas imagens."""
    return model.batch_generate_images(prompts, **kwargs)

def generate_and_upload(prompt: str, job_id: str, **kwargs) -> Optional[str]:
    """Interface para geração e upload de imagem."""
    return model.generate_and_upload(prompt, job_id, **kwargs)

def get_model() -> SDXLModel:
    """Retorna a instância global do modelo, criando se necessário."""
    global model
    if model is None:
        model = SDXLModel()
    return model

def set_model_config(config: dict) -> None:
    """
    Atualiza a configuração do modelo.
    
    Args:
        config: Dicionário com novas configurações
    """
    SDXL_CONFIG.update(config)
    logger.info("Configuração do modelo atualizada")

def generate_image(
    prompt: str,
    width: int = SDXL_CONFIG["width"],
    height: int = SDXL_CONFIG["height"],
    steps: int = SDXL_CONFIG["num_inference_steps"],
    seed: Optional[int] = None
) -> Optional[Path]:
    """
    Gera uma única imagem.
    
    Args:
        prompt: Texto descritivo
        width: Largura da imagem
        height: Altura da imagem
        steps: Passos de inferência
        seed: Seed para reprodutibilidade
        
    Returns:
        Path do arquivo gerado ou None se falhar
    """
    try:
        # Usa a instância global do modelo
        global model
        if model is None:
            model = SDXLModel()
            
        # Chama o método da instância do modelo
        return model.generate_image(
            prompt=prompt,
            width=width,
            height=height,
            steps=steps,
            seed=seed
        )
    except Exception as e:
        logger.error(f"Erro na geração: {e}")
        return None

def batch_generate_images(
    prompts: List[str],
    **kwargs
) -> List[Optional[Path]]:
    """
    Gera múltiplas imagens em batch.
    
    Args:
        prompts: Lista de prompts
        **kwargs: Argumentos adicionais para generate_image
        
    Returns:
        Lista de paths dos arquivos gerados (None para falhas)
    """
    try:
        # Usa a instância global do modelo
        global model
        if model is None:
            model = SDXLModel()
            
        # Chama o método da instância do modelo
        return model.batch_generate_images(prompts=prompts, **kwargs)
    except Exception as e:
        logger.error(f"Erro na geração em batch: {e}")
        return [None] * len(prompts)
