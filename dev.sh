#!/bin/bash

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Função para verificar se um comando existe
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}Erro: $1 não está instalado${NC}"
        exit 1
    fi
}

# Função para criar diretório de logs
create_log_dir() {
    mkdir -p logs
}

# Função para verificar se o Docker está rodando
check_docker_running() {
    if ! docker info >/dev/null 2>&1; then
        echo -e "${RED}Erro: Docker não está rodando${NC}"
        echo -e "${YELLOW}Por favor, inicie o Docker Desktop e tente novamente${NC}"
        exit 1
    fi
}

# Função para parar containers antigos se existirem
stop_existing_containers() {
    echo -e "${YELLOW}Verificando containers antigos...${NC}"
    docker rm -f redis minio 2>/dev/null
}

# Verifica dependências necessárias
echo -e "${YELLOW}Verificando dependências...${NC}"
check_command "python3"
check_command "docker"

# Verifica se o Docker está rodando
check_docker_running

# Para containers antigos
stop_existing_containers

# Verifica se o ambiente virtual existe e está ativado
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Ambiente virtual não encontrado. Executando setup...${NC}"
    python3 setup.py
fi

# Ativa o ambiente virtual
source venv/bin/activate

# Verifica se os containers do Redis e MinIO estão rodando
if ! docker ps | grep -q "redis"; then
    echo -e "${YELLOW}Iniciando Redis...${NC}"
    docker run -d -p 6379:6379 --name redis redis:alpine
fi

if ! docker ps | grep -q "minio"; then
    echo -e "${YELLOW}Iniciando MinIO...${NC}"
    docker run -d -p 9000:9000 -p 9090:9090 \
        -e MINIO_ROOT_USER=minioadmin \
        -e MINIO_ROOT_PASSWORD=minioadmin \
        --name minio \
        minio/minio server /data
fi

# Cria diretório de logs
create_log_dir

# Inicia o Celery em background
echo -e "${YELLOW}Iniciando Celery worker...${NC}"
celery -A celery_app worker --loglevel=INFO > logs/celery.log 2>&1 &
CELERY_PID=$!

# Inicia o Flower em background
echo -e "${YELLOW}Iniciando Flower...${NC}"
celery -A celery_app flower --port=5555 > logs/flower.log 2>&1 &
FLOWER_PID=$!

# Inicia a API
echo -e "${YELLOW}Iniciando API...${NC}"
uvicorn app:app --host 0.0.0.0 --port 8000 --reload > logs/api.log 2>&1 &
API_PID=$!

# Aguarda um momento para os serviços iniciarem
sleep 5

# Verifica se os processos estão rodando
if ps -p $CELERY_PID > /dev/null && ps -p $API_PID > /dev/null; then
    echo -e "${GREEN}Todos os serviços iniciados com sucesso!${NC}"
    echo -e "${GREEN}API disponível em: http://localhost:8000${NC}"
    echo -e "${GREEN}Documentação da API: http://localhost:8000/docs${NC}"
    echo -e "${GREEN}MinIO Console: http://localhost:9090${NC}"
    echo -e "${GREEN}Flower (Monitoramento Celery): http://localhost:5555${NC}"
else
    echo -e "${RED}Erro: Alguns serviços não iniciaram corretamente${NC}"
    echo "Verifique os logs em ./logs/"
    exit 1
fi

# Função para limpar processos ao sair
cleanup() {
    echo -e "${YELLOW}Encerrando serviços...${NC}"
    kill $CELERY_PID 2>/dev/null
    kill $FLOWER_PID 2>/dev/null
    kill $API_PID 2>/dev/null
    exit 0
}

# Registra a função de cleanup para ser chamada ao sair
trap cleanup SIGINT SIGTERM

# Mantém o script rodando e mostra logs
echo -e "${YELLOW}Mostrando logs dos serviços...${NC}"
tail -f logs/*.log 