"""
Pacote de edição e composição de vídeos.
Este pacote contém a implementação do sistema de edição de vídeos usando MoviePy.

Documentação:
- Combina imagens e áudios em vídeos
- Suporta múltiplas cenas com diferentes durações
- Permite ajustes de resolução, FPS e qualidade
- Otimizado para processamento em batch
"""

from .editor import create_video_from_scenes

# Exporta a função principal para uso direto
# Exemplo de uso:
# from video import create_video_from_scenes
# video_url = create_video_from_scenes(job_id, scenes)
