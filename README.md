# 🎬 Gerador de Vídeos com IA

Sistema de geração automática de vídeos utilizando Inteligência Artificial para criar imagens, sintetizar voz e compor vídeos.

## 🚀 Funcionalidades

- 🖼️ **Geração de Imagens**: Stable Diffusion XL para criar imagens em alta qualidade
- 🗣️ **Síntese de Voz**: Fish Speech TTS com suporte a múltiplas vozes e clonagem de voz
- 🎥 **Composição de Vídeos**: MoviePy para combinar imagens e áudio em vídeos
- 🔄 **Processamento Assíncrono**: Celery + Redis para processamento em background
- 📦 **Armazenamento**: MinIO para armazenamento seguro de arquivos
- 🔒 **API Segura**: Autenticação via API Key e endpoints RESTful

## 🛠️ Requisitos

### Hardware
- GPU NVIDIA com suporte CUDA (mínimo 8GB VRAM)
- 16GB RAM
- 20GB de espaço em disco
ffff
### Software
- Python 3.9+
- CUDA Toolkit 11.8+
- FFmpeg
- Docker (opcional, para Redis/MinIO)

## 📦 Instalação

1. Clone o repositório:
```bash
git clone https://seu-repositorio/simpleapi.git
cd simpleapi
```

2. Crie e ative um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
.\venv\Scripts\activate  # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Configure as variáveis de ambiente:
```bash
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

5. Baixe os modelos de IA:
```bash
python download_models.py
```

## ⚙️ Configuração

### MinIO
```bash
# Exemplo usando Docker
docker run -d -p 9000:9000 -p 9090:9090 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data
```

### Redis
```bash
# Exemplo usando Docker
docker run -d -p 6379:6379 redis:alpine
```

### Banco de Dados
```bash
# Inicializa o banco SQLite e aplica as migrações
alembic upgrade head
```

## 🚀 Execução

1. Inicie o worker Celery:
```bash
celery -A celery_app worker --loglevel=INFO
```

2. Inicie o servidor da API:
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

3. Acesse a documentação da API:
```
http://localhost:8000/docs
```

## 📝 Exemplos de Uso

### Gerando um Vídeo
```python
import requests

api_key = "sua-chave-api"
headers = {"X-API-Key": api_key}

# Dados para geração do vídeo
data = {
    "segments": [
        {
            "image_prompt": "Uma paisagem de montanhas ao pôr-do-sol",
            "text": "Era uma vez, nas montanhas distantes...",
            "voice": "male_1"
        }
    ]
}

# Inicia a geração
response = requests.post(
    "http://localhost:8000/generate-video",
    headers=headers,
    json=data
)

job_id = response.json()["job_id"]

# Consulta o status
status = requests.get(
    f"http://localhost:8000/status/{job_id}",
    headers=headers
)

print(status.json())
```

## 📁 Estrutura do Projeto

```
project/
├── app.py                  # API principal (FastAPI)
├── celery_app.py          # Configuração do Celery
├── config.py              # Configurações gerais
├── requirements.txt       # Dependências do projeto
├── models/               # Modelos baixados localmente
│   ├── sdxl/            # Stable Diffusion XL
│   └── fish_speech/     # Fish Speech
├── stable_diffusion/    # Geração de imagens
├── tts/                 # Síntese de voz
├── video/              # Edição de vídeos
├── tasks/              # Tarefas Celery
├── storage/            # Gerenciamento de arquivos
└── db/                 # Banco de dados SQLite
```

## 🔒 Segurança

- Todas as requisições requerem uma API Key válida
- Arquivos são armazenados de forma segura no MinIO
- URLs pré-assinadas com tempo de expiração
- Sanitização de inputs e validação de dados

## 📚 Documentação Adicional

- [Documentação da API](http://localhost:8000/docs)
- [Configurações Avançadas](docs/advanced.md)
- [Guia de Desenvolvimento](docs/development.md)

## 🤝 Contribuindo

1. Fork o projeto
2. Crie sua branch de feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 👥 Autores

- **Seu Nome** - *Trabalho Inicial* - [SeuGitHub](https://github.com/seugithub)

## 🙏 Agradecimentos

- Stability AI pelo modelo Stable Diffusion XL
- Fish Speech pelo modelo TTS
- Comunidade de código aberto 