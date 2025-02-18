"""
Pacote de geração de imagens usando Stable Diffusion XL.
Este pacote contém a implementação do sistema de geração de imagens.

Documentação:
- Utiliza o modelo Stable Diffusion XL para geração de alta qualidade
- Suporta múltiplas resoluções e configurações
- Otimizado para GPU com processamento em batch
- Integrado com sistema de cache para prompts repetidos
"""

from .sdxl_model import (
    generate_image,
    batch_generate_images,
    set_model_config
)

# Exporta apenas as funções necessárias
__all__ = [
    'generate_image',
    'batch_generate_images',
    'set_model_config'
]

# Exemplos de uso:
# from stable_diffusion import generate_image
# image_path = generate_image(
#     prompt="Uma paisagem de montanhas ao pôr-do-sol",
#     width=1280,
#     height=720
# )
#
# from stable_diffusion import batch_generate_images
# image_paths = batch_generate_images([
#     "Uma paisagem de montanhas",
#     "Um rio sob o céu estrelado"
# ])
