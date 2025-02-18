#!/bin/bash

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Diretório do script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOG_DIR="$SCRIPT_DIR/logs/supervisor"

# Cria diretório de logs se não existir
mkdir -p "$LOG_DIR"

# Função para verificar status de um serviço
check_service() {
    local service=$1
    local status=$(supervisorctl status "$service" | awk '{print $2}')
    if [ "$status" = "RUNNING" ]; then
        return 0
    else
        return 1
    fi
}

# Função para aguardar serviço iniciar/parar
wait_for_service() {
    local service=$1
    local action=$2  # "start" ou "stop"
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if [ "$action" = "start" ]; then
            if check_service "$service"; then
                return 0
            fi
        else
            if ! check_service "$service"; then
                return 0
            fi
        fi
        echo -n "."
        sleep 1
        attempt=$((attempt + 1))
    done
    return 1
}

# Lista de serviços
services=("api" "celery" "flower")

# Para cada serviço
echo -e "${YELLOW}Parando serviços...${NC}"
for service in "${services[@]}"; do
    echo -n "Parando $service "
    supervisorctl stop "$service" > /dev/null
    if wait_for_service "$service" "stop"; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}Timeout${NC}"
    fi
done

echo -e "${YELLOW}Iniciando serviços...${NC}"
for service in "${services[@]}"; do
    echo -n "Iniciando $service "
    supervisorctl start "$service" > /dev/null
    if wait_for_service "$service" "start"; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}Falha${NC}"
        # Mostra últimas linhas do log em caso de falha
        echo -e "${RED}Últimas linhas do log:${NC}"
        tail -n 5 "$LOG_DIR/$service.err.log"
    fi
done

echo -e "\n${YELLOW}Status dos serviços:${NC}"
supervisorctl status

echo -e "\n${YELLOW}Verificando logs por erros:${NC}"
for service in "${services[@]}"; do
    if [ -f "$LOG_DIR/$service.err.log" ] && [ -s "$LOG_DIR/$service.err.log" ]; then
        echo -e "${RED}Erros encontrados em $service:${NC}"
        tail -n 3 "$LOG_DIR/$service.err.log"
    fi
done 