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
import psutil

from config import SDXL_CONFIG, SDXL_MODEL_PATH, DEVICE
from storage import upload_file, get_presigned_url

class SDXLConfigError(Exception):
    """Erro de configuração do SDXL."""
    pass

class SDXLResourceError(Exception):
    """Erro de recursos do SDXL."""
    pass

class SDXLModel:
    """Classe para gerenciar o modelo Stable Diffusion XL."""
    
    REQUIRED_CONFIG_KEYS = [
        "width", "height", "num_inference_steps", "guidance_scale",
        "negative_prompt", "use_fp16", "enable_vae_tiling", "torch_compile"
    ]
    
    MIN_WIDTH = 512
    MAX_WIDTH = 2048
    MIN_HEIGHT = 512
    MAX_HEIGHT = 2048
    MIN_STEPS = 1
    MAX_STEPS = 150
    
    def __init__(self):
        """Inicializa o modelo SDXL com configurações otimizadas."""
        try:
            logger.info("Iniciando inicialização do modelo SDXL...")
            
            # Valida configurações
            self._validate_config()
            
            # Verifica recursos disponíveis
            self._check_resources()
            
            self.device = DEVICE
            logger.info(f"Usando dispositivo: {self.device}")
            
            self.pipe = None
            self.temp_dir = Path(tempfile.mkdtemp())
            logger.info(f"Diretório temporário criado: {self.temp_dir}")
            
            # Configurações do modelo com validação
            self.width = self._validate_dimension(SDXL_CONFIG["width"], "width")
            self.height = self._validate_dimension(SDXL_CONFIG["height"], "height")
            self.steps = self._validate_steps(SDXL_CONFIG["num_inference_steps"])
            self.guidance_scale = SDXL_CONFIG["guidance_scale"]
            self.negative_prompt = SDXL_CONFIG["negative_prompt"]
            
            # Carrega o modelo
            self._load_model()
            logger.info(f"SDXL inicializado no dispositivo: {self.device}")
            
        except SDXLConfigError as e:
            logger.error(f"Erro de configuração do SDXL: {str(e)}")
            raise
        except SDXLResourceError as e:
            logger.error(f"Erro de recursos do SDXL: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Erro na inicialização do SDXL: {str(e)}")
            raise

    def _validate_config(self) -> None:
        """Valida as configurações do SDXL."""
        # Verifica se todas as chaves necessárias existem
        missing_keys = [key for key in self.REQUIRED_CONFIG_KEYS if key not in SDXL_CONFIG]
        if missing_keys:
            raise SDXLConfigError(f"Configurações ausentes: {', '.join(missing_keys)}")
            
        # Valida tipos de dados
        if not isinstance(SDXL_CONFIG["width"], int):
            raise SDXLConfigError("width deve ser um número inteiro")
        if not isinstance(SDXL_CONFIG["height"], int):
            raise SDXLConfigError("height deve ser um número inteiro")
        if not isinstance(SDXL_CONFIG["num_inference_steps"], int):
            raise SDXLConfigError("num_inference_steps deve ser um número inteiro")
        if not isinstance(SDXL_CONFIG["guidance_scale"], (int, float)):
            raise SDXLConfigError("guidance_scale deve ser um número")
        if not isinstance(SDXL_CONFIG["negative_prompt"], str):
            raise SDXLConfigError("negative_prompt deve ser uma string")
            
        logger.info("Configurações validadas com sucesso")

    def _check_resources(self) -> None:
        """Verifica se há recursos suficientes disponíveis."""
        # Verifica memória RAM
        available_ram = psutil.virtual_memory().available / (1024 * 1024 * 1024)  # GB
        if available_ram < 8:  # Mínimo de 8GB
            raise SDXLResourceError(f"Memória RAM insuficiente: {available_ram:.1f}GB disponível")
            
        # Verifica GPU se disponível
        if torch.cuda.is_available():
            try:
                gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024 * 1024 * 1024)  # GB
                if gpu_memory < 6:  # Mínimo de 6GB
                    raise SDXLResourceError(f"Memória GPU insuficiente: {gpu_memory:.1f}GB disponível")
            except Exception as e:
                logger.warning(f"Não foi possível verificar memória GPU: {e}")
                
        # Verifica espaço em disco
        temp_dir = Path(tempfile.gettempdir())
        free_space = shutil.disk_usage(temp_dir).free / (1024 * 1024 * 1024)  # GB
        if free_space < 10:  # Mínimo de 10GB
            raise SDXLResourceError(f"Espaço em disco insuficiente: {free_space:.1f}GB disponível")
            
        logger.info("Verificação de recursos concluída com sucesso")

    def _validate_dimension(self, value: int, name: str) -> int:
        """Valida dimensões de imagem."""
        if not isinstance(value, int):
            raise SDXLConfigError(f"{name} deve ser um número inteiro")
            
        min_val = getattr(self, f"MIN_{name.upper()}")
        max_val = getattr(self, f"MAX_{name.upper()}")
        
        if value < min_val or value > max_val:
            raise SDXLConfigError(
                f"{name} deve estar entre {min_val} e {max_val}, recebido: {value}"
            )
            
        return value

    def _validate_steps(self, steps: int) -> int:
        """Valida número de passos de inferência."""
        if not isinstance(steps, int):
            raise SDXLConfigError("steps deve ser um número inteiro")
            
        if steps < self.MIN_STEPS or steps > self.MAX_STEPS:
            raise SDXLConfigError(
                f"steps deve estar entre {self.MIN_STEPS} e {self.MAX_STEPS}, recebido: {steps}"
            )
            
        return steps

    def _load_model(self) -> None:
        """Carrega o modelo SDXL com otimizações."""
        try:
            logger.info("Iniciando carregamento do modelo SDXL...")
            
            # Valida caminho do modelo
            if not SDXL_MODEL_PATH:
                raise SDXLConfigError("Caminho do modelo não definido")
            
            # Converte PosixPath para string se necessário
            model_path = str(SDXL_MODEL_PATH) if isinstance(SDXL_MODEL_PATH, Path) else SDXL_MODEL_PATH
            
            # Verifica se é um caminho local ou HuggingFace
            if os.path.exists(model_path):
                logger.info(f"Usando modelo local: {model_path}")
            else:
                logger.info(f"Baixando modelo do HuggingFace: {model_path}")
            
            # Carrega o modelo com tratamento de erros
            try:
                self.pipe = DiffusionPipeline.from_pretrained(
                    model_path,
                    torch_dtype=torch.float16 if SDXL_CONFIG["use_fp16"] else torch.float32,
                    use_safetensors=True,
                    variant="fp16" if SDXL_CONFIG["use_fp16"] else None
                )
            except Exception as e:
                raise SDXLConfigError(f"Erro ao carregar modelo: {str(e)}")

            # Move para GPU se disponível
            if torch.cuda.is_available():
                try:
                    logger.info("Movendo modelo para GPU...")
                    self.pipe = self.pipe.to(self.device)
                    
                    # Habilita otimizações
                    if hasattr(self.pipe, 'enable_xformers_memory_efficient_attention'):
                        self.pipe.enable_xformers_memory_efficient_attention()
                        logger.info("Otimização xformers habilitada")
                    
                    # Habilita otimização de memória
                    if hasattr(self.pipe, 'enable_model_cpu_offload'):
                        self.pipe.enable_model_cpu_offload()
                        logger.info("Otimização de memória habilitada")

                    # Habilita VAE tiling se configurado
                    if SDXL_CONFIG["enable_vae_tiling"]:
                        self.pipe.vae.enable_tiling()
                        logger.info("VAE tiling habilitado")

                    # Compila o modelo se configurado
                    if SDXL_CONFIG["torch_compile"] and hasattr(torch, 'compile'):
                        try:
                            self.pipe.unet = torch.compile(
                                self.pipe.unet, 
                                mode="reduce-overhead", 
                                fullgraph=True
                            )
                            logger.info("Modelo compilado com sucesso")
                        except Exception as e:
                            logger.warning(f"Não foi possível compilar o modelo: {e}")
                except Exception as e:
                    raise SDXLResourceError(f"Erro ao configurar GPU: {str(e)}")

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
            
        Raises:
            SDXLConfigError: Se os parâmetros forem inválidos
            SDXLResourceError: Se não houver recursos suficientes
            RuntimeError: Para outros erros de execução
        """
        try:
            # Validações básicas
            if not prompt or not isinstance(prompt, str):
                raise SDXLConfigError("Prompt deve ser uma string não vazia")
                
            if len(prompt) > 1000:
                raise SDXLConfigError("Prompt muito longo (máximo 1000 caracteres)")
                
            if seed is not None and not isinstance(seed, int):
                raise SDXLConfigError("Seed deve ser um número inteiro")
                
            # Valida dimensões personalizadas
            if width is not None:
                width = self._validate_dimension(width, "width")
            if height is not None:
                height = self._validate_dimension(height, "height")
            if steps is not None:
                steps = self._validate_steps(steps)
                
            # Verifica memória disponível
            if torch.cuda.is_available():
                free_memory = torch.cuda.get_device_properties(0).total_memory - torch.cuda.memory_allocated()
                if free_memory < 2 * 1024 * 1024 * 1024:  # 2GB
                    logger.warning("Pouca memória GPU disponível, limpando cache...")
                    torch.cuda.empty_cache()
                    gc.collect()
            
            return self.batch_generate_images(
                prompts=[prompt],
                seeds=[seed] if seed is not None else None,
                width=width,
                height=height,
                steps=steps
            )[0]
            
        except Exception as e:
            logger.error(f"Erro ao gerar imagem: {str(e)}")
            self._cleanup_temp_files()
            raise

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
            SDXLConfigError: Se os parâmetros forem inválidos
            SDXLResourceError: Se não houver recursos suficientes
            RuntimeError: Para outros erros de execução
        """
        try:
            # Validações de entrada
            if not prompts:
                raise SDXLConfigError("Lista de prompts não pode estar vazia")
            
            if any(not isinstance(p, str) or not p.strip() for p in prompts):
                raise SDXLConfigError("Todos os prompts devem ser strings não vazias")
                
            if any(len(p) > 1000 for p in prompts):
                raise SDXLConfigError("Prompts muito longos (máximo 1000 caracteres)")
                
            if seeds is not None:
                if len(seeds) != len(prompts):
                    raise SDXLConfigError("Número de seeds deve ser igual ao número de prompts")
                if any(not isinstance(s, int) for s in seeds if s is not None):
                    raise SDXLConfigError("Seeds devem ser números inteiros")
                
            if batch_size < 1:
                raise SDXLConfigError("Tamanho do batch deve ser maior que zero")
                
            if batch_size > len(prompts):
                batch_size = len(prompts)
                logger.warning(f"Batch size ajustado para {batch_size} (número de prompts)")
            
            # Valida dimensões personalizadas
            if width is not None:
                width = self._validate_dimension(width, "width")
            if height is not None:
                height = self._validate_dimension(height, "height")
            if steps is not None:
                steps = self._validate_steps(steps)
            
            # Usa valores padrão se não especificados
            width = width or self.width
            height = height or self.height
            steps = steps or self.steps
            
            # Prepara seeds se não fornecidas
            if seeds is None:
                seeds = [None] * len(prompts)
            
            # Lista para armazenar resultados
            image_paths = []
            
            # Processa em batches
            for i in range(0, len(prompts), batch_size):
                # Verifica memória antes de cada batch
                if torch.cuda.is_available():
                    free_memory = torch.cuda.get_device_properties(0).total_memory - torch.cuda.memory_allocated()
                    if free_memory < 2 * 1024 * 1024 * 1024:  # 2GB
                        logger.warning("Pouca memória GPU disponível, limpando cache...")
                        torch.cuda.empty_cache()
                        gc.collect()
                
                batch_prompts = prompts[i:i + batch_size]
                batch_seeds = seeds[i:i + batch_size]
                
                try:
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
                        try:
                            image_path = self.temp_dir / f"{uuid.uuid4()}.png"
                            image.save(image_path, format="PNG", quality=95)
                            image_paths.append(str(image_path))
                        except Exception as e:
                            logger.error(f"Erro ao salvar imagem {j} do batch: {e}")
                            continue
                    
                except Exception as e:
                    logger.error(f"Erro no batch {i}: {e}")
                    continue
                finally:
                    # Limpa memória GPU
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    gc.collect()
            
            if not image_paths:
                raise RuntimeError("Nenhuma imagem foi gerada com sucesso")
                
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
            SDXLConfigError: Se os parâmetros forem inválidos
            SDXLResourceError: Se não houver recursos suficientes
            torch.cuda.OutOfMemoryError: Se não houver memória GPU suficiente
        """
        if not self.pipe:
            raise RuntimeError("Modelo não foi inicializado corretamente")
            
        try:
            # Verifica memória antes da geração
            if torch.cuda.is_available():
                free_memory = torch.cuda.get_device_properties(0).total_memory - torch.cuda.memory_allocated()
                if free_memory < 2 * 1024 * 1024 * 1024:  # 2GB
                    logger.warning("Pouca memória GPU disponível, limpando cache...")
                    torch.cuda.empty_cache()
                    gc.collect()
            
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
                raise SDXLResourceError(f"Erro de memória GPU: {str(e)}. Tente reduzir o tamanho do batch ou da imagem.")
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
            
        Raises:
            SDXLConfigError: Se os parâmetros forem inválidos
            SDXLResourceError: Se não houver recursos suficientes
            RuntimeError: Para outros erros de execução
        """
        try:
            # Validações básicas
            if not prompt or not isinstance(prompt, str):
                raise SDXLConfigError("Prompt deve ser uma string não vazia")
                
            if not job_id or not isinstance(job_id, str):
                raise SDXLConfigError("job_id deve ser uma string não vazia")
            
            # Gera a imagem
            image_path = self.generate_image(prompt, **kwargs)
            if image_path is None:
                raise RuntimeError("Falha na geração da imagem")
            
            # Verifica se o arquivo foi gerado
            if not os.path.exists(image_path):
                raise RuntimeError(f"Arquivo de imagem não encontrado: {image_path}")
            
            # Faz upload para o MinIO
            object_name = f"images/{job_id}.png"
            url = upload_file(image_path, object_name)
            
            if not url:
                raise RuntimeError("Falha no upload da imagem para o MinIO")
            
            # Limpa arquivo temporário
            try:
                if os.path.exists(image_path):
                    os.remove(image_path)
            except Exception as e:
                logger.warning(f"Erro ao remover arquivo temporário: {e}")
            
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
    """
    Interface para geração de uma única imagem.
    
    Args:
        prompt: Texto descritivo
        **kwargs: Argumentos adicionais para o método generate_image
        
    Returns:
        Path do arquivo gerado ou None em caso de erro
        
    Raises:
        SDXLConfigError: Se os parâmetros forem inválidos
        SDXLResourceError: Se não houver recursos suficientes
        RuntimeError: Para outros erros de execução
    """
    try:
        # Valida prompt
        if not prompt or not isinstance(prompt, str):
            raise SDXLConfigError("Prompt deve ser uma string não vazia")
            
        # Valida argumentos adicionais
        for key, value in kwargs.items():
            if key not in ["width", "height", "steps", "seed"]:
                raise SDXLConfigError(f"Argumento inválido: {key}")
        
        # Usa a instância global do modelo
        global model
        if model is None:
            model = SDXLModel()
            
        # Chama o método da instância do modelo
        return model.generate_image(prompt=prompt, **kwargs)
        
    except Exception as e:
        logger.error(f"Erro na interface generate_image: {str(e)}")
        return None

def batch_generate_images(prompts: List[str], **kwargs) -> List[str]:
    """
    Interface para geração de múltiplas imagens.
    
    Args:
        prompts: Lista de prompts
        **kwargs: Argumentos adicionais para o método batch_generate_images
        
    Returns:
        Lista de paths dos arquivos gerados
        
    Raises:
        SDXLConfigError: Se os parâmetros forem inválidos
        SDXLResourceError: Se não houver recursos suficientes
        RuntimeError: Para outros erros de execução
    """
    try:
        # Valida prompts
        if not prompts:
            raise SDXLConfigError("Lista de prompts não pode estar vazia")
            
        if not isinstance(prompts, list):
            raise SDXLConfigError("prompts deve ser uma lista de strings")
            
        if any(not isinstance(p, str) or not p.strip() for p in prompts):
            raise SDXLConfigError("Todos os prompts devem ser strings não vazias")
            
        # Valida argumentos adicionais
        for key, value in kwargs.items():
            if key not in ["width", "height", "steps", "seeds", "batch_size"]:
                raise SDXLConfigError(f"Argumento inválido: {key}")
        
        # Usa a instância global do modelo
        global model
        if model is None:
            model = SDXLModel()
            
        # Chama o método da instância do modelo
        return model.batch_generate_images(prompts=prompts, **kwargs)
        
    except Exception as e:
        logger.error(f"Erro na interface batch_generate_images: {str(e)}")
        return []

def generate_and_upload(prompt: str, job_id: str, **kwargs) -> Optional[str]:
    """
    Interface para geração e upload de imagem.
    
    Args:
        prompt: Texto descritivo
        job_id: ID do job para identificação
        **kwargs: Argumentos adicionais para o método generate_and_upload
        
    Returns:
        URL da imagem no MinIO ou None em caso de erro
        
    Raises:
        SDXLConfigError: Se os parâmetros forem inválidos
        SDXLResourceError: Se não houver recursos suficientes
        RuntimeError: Para outros erros de execução
    """
    try:
        # Valida prompt e job_id
        if not prompt or not isinstance(prompt, str):
            raise SDXLConfigError("Prompt deve ser uma string não vazia")
            
        if not job_id or not isinstance(job_id, str):
            raise SDXLConfigError("job_id deve ser uma string não vazia")
            
        # Valida argumentos adicionais
        for key, value in kwargs.items():
            if key not in ["width", "height", "steps", "seed"]:
                raise SDXLConfigError(f"Argumento inválido: {key}")
        
        # Usa a instância global do modelo
        global model
        if model is None:
            model = SDXLModel()
            
        # Chama o método da instância do modelo
        return model.generate_and_upload(prompt=prompt, job_id=job_id, **kwargs)
        
    except Exception as e:
        logger.error(f"Erro na interface generate_and_upload: {str(e)}")
        return None

def get_model() -> SDXLModel:
    """
    Retorna a instância global do modelo, criando se necessário.
    
    Returns:
        Instância do modelo SDXL
        
    Raises:
        SDXLConfigError: Se houver erro na configuração
        SDXLResourceError: Se não houver recursos suficientes
        RuntimeError: Para outros erros de execução
    """
    try:
        global model
        if model is None:
            model = SDXLModel()
        return model
    except Exception as e:
        logger.error(f"Erro ao obter instância do modelo: {str(e)}")
        raise

def set_model_config(config: dict) -> None:
    """
    Atualiza a configuração do modelo.
    
    Args:
        config: Dicionário com novas configurações
        
    Raises:
        SDXLConfigError: Se as configurações forem inválidas
        RuntimeError: Para outros erros de execução
    """
    try:
        # Valida configuração
        if not isinstance(config, dict):
            raise SDXLConfigError("config deve ser um dicionário")
            
        # Valida chaves permitidas
        allowed_keys = {
            "width", "height", "num_inference_steps", "guidance_scale",
            "negative_prompt", "use_fp16", "enable_vae_tiling", "torch_compile"
        }
        
        invalid_keys = set(config.keys()) - allowed_keys
        if invalid_keys:
            raise SDXLConfigError(f"Chaves de configuração inválidas: {', '.join(invalid_keys)}")
            
        # Valida tipos e valores
        if "width" in config:
            if not isinstance(config["width"], int) or config["width"] < 512 or config["width"] > 2048:
                raise SDXLConfigError("width deve ser um inteiro entre 512 e 2048")
                
        if "height" in config:
            if not isinstance(config["height"], int) or config["height"] < 512 or config["height"] > 2048:
                raise SDXLConfigError("height deve ser um inteiro entre 512 e 2048")
                
        if "num_inference_steps" in config:
            if not isinstance(config["num_inference_steps"], int) or config["num_inference_steps"] < 1 or config["num_inference_steps"] > 150:
                raise SDXLConfigError("num_inference_steps deve ser um inteiro entre 1 e 150")
                
        if "guidance_scale" in config:
            if not isinstance(config["guidance_scale"], (int, float)) or config["guidance_scale"] < 1 or config["guidance_scale"] > 20:
                raise SDXLConfigError("guidance_scale deve ser um número entre 1 e 20")
                
        if "negative_prompt" in config:
            if not isinstance(config["negative_prompt"], str):
                raise SDXLConfigError("negative_prompt deve ser uma string")
                
        if "use_fp16" in config:
            if not isinstance(config["use_fp16"], bool):
                raise SDXLConfigError("use_fp16 deve ser um booleano")
                
        if "enable_vae_tiling" in config:
            if not isinstance(config["enable_vae_tiling"], bool):
                raise SDXLConfigError("enable_vae_tiling deve ser um booleano")
                
        if "torch_compile" in config:
            if not isinstance(config["torch_compile"], bool):
                raise SDXLConfigError("torch_compile deve ser um booleano")
        
        # Atualiza configuração
        SDXL_CONFIG.update(config)
        logger.info("Configuração do modelo atualizada com sucesso")
        
    except Exception as e:
        logger.error(f"Erro ao atualizar configuração do modelo: {str(e)}")
        raise
