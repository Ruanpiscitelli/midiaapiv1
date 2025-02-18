#!/bin/bash

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Diretórios
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$PROJECT_DIR/venv"
LOG_DIR="$PROJECT_DIR/logs"
SUPERVISOR_LOG_DIR="$LOG_DIR/supervisor"

# Função para verificar se um comando existe
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}Erro: $1 não está instalado${NC}"
        exit 1
    fi
}

# Função para verificar se um processo está rodando
check_process() {
    pgrep -f "$1" &> /dev/null
}

# Função para criar diretórios de logs
setup_log_dirs() {
    mkdir -p "$LOG_DIR"
    mkdir -p "$SUPERVISOR_LOG_DIR"
    chmod -R 755 "$LOG_DIR"
}

# Função para limpar processos antigos
cleanup_old_processes() {
    echo -e "${YELLOW}Limpando processos antigos...${NC}"
    pkill -f "celery"
    pkill -f "flower"
    pkill -f "uvicorn"
    sleep 2
}

# Função para verificar ambiente virtual
check_venv() {
    if [ -z "$VIRTUAL_ENV" ]; then
        if [ ! -f "$VENV_DIR/bin/activate" ]; then
            echo -e "${YELLOW}Ambiente virtual não encontrado. Executando setup...${NC}"
            python3 setup.py
        fi
        echo -e "${YELLOW}Ativando ambiente virtual...${NC}"
        source "$VENV_DIR/bin/activate"
    fi
}

# Função para verificar status dos serviços
check_services() {
    local all_running=true
    
    if ! check_process "celery"; then
        echo -e "${RED}Erro: Celery não está rodando${NC}"
        all_running=false
    fi
    
    if ! check_process "uvicorn"; then
        echo -e "${RED}Erro: API não está rodando${NC}"
        all_running=false
    fi
    
    if ! docker ps | grep -q "redis"; then
        echo -e "${RED}Erro: Redis não está rodando${NC}"
        all_running=false
    fi
    
    if ! docker ps | grep -q "minio"; then
        echo -e "${RED}Erro: MinIO não está rodando${NC}"
        all_running=false
    fi
    
    if [ "$all_running" = false ]; then
        return 1
    fi
    return 0
}

# Início do script principal
echo -e "${YELLOW}Iniciando serviços...${NC}"

# Verifica dependências necessárias
check_command "python3"
check_command "docker"
check_command "supervisord"

# Configura diretórios de logs
setup_log_dirs

# Limpa processos antigos
cleanup_old_processes

# Verifica e ativa ambiente virtual
check_venv

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

# Inicia o Supervisor
echo -e "${YELLOW}Iniciando serviços via Supervisor...${NC}"
supervisord -c supervisord.conf

# Aguarda serviços iniciarem
echo -e "${YELLOW}Aguardando serviços iniciarem...${NC}"
for i in {1..30}; do
    if check_services; then
        echo -e "${GREEN}Todos os serviços iniciados com sucesso!${NC}"
        echo -e "${GREEN}API disponível em: http://localhost:8000${NC}"
        echo -e "${GREEN}Documentação da API: http://localhost:8000/docs${NC}"
        echo -e "${GREEN}MinIO Console: http://localhost:9090${NC}"
        echo -e "${GREEN}Flower (Monitoramento Celery): http://localhost:5555${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}Timeout: Alguns serviços não iniciaram corretamente${NC}"
        echo -e "${YELLOW}Verificando logs para diagnóstico...${NC}"
        tail -n 50 "$SUPERVISOR_LOG_DIR"/*.log
        exit 1
    fi
    sleep 1
done

# Monitora logs
echo -e "${YELLOW}Monitorando logs dos serviços...${NC}"
exec tail -f "$SUPERVISOR_LOG_DIR"/*.log 