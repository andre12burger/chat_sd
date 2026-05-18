#!/bin/bash

# Start Script para Deploy no Render.com
# Este script inicia o Chat Engine, o Backup Server e o Web Gateway

set -e

CHAT_ENGINE_PID=""
BACKUP_SERVER_PID=""

cleanup() {
	echo "Encerrando processos em background..."

	if [ -n "$BACKUP_SERVER_PID" ]; then
		kill "$BACKUP_SERVER_PID" 2>/dev/null || true
	fi

	if [ -n "$CHAT_ENGINE_PID" ]; then
		kill "$CHAT_ENGINE_PID" 2>/dev/null || true
	fi
}

trap cleanup EXIT

echo "=========================================="
echo "Chat Distribuído - Inicializando..."
echo "=========================================="

# Aguarda alguns segundos para garantir que o ambiente está pronto
sleep 2

# Inicia o Chat Engine em background (porta 5000 local)
echo "Iniciando Chat Engine na porta 5000 (localhost)..."
python backend/chat_engine.py > logs_engine.txt 2>&1 &
CHAT_ENGINE_PID=$!
echo "Chat Engine iniciado (PID: $CHAT_ENGINE_PID)"

# Inicia o servidor de backup em background
echo "Iniciando Backup Server..."
python backend/backup_server.py > logs_backup.txt 2>&1 &
BACKUP_SERVER_PID=$!
echo "Backup Server iniciado (PID: $BACKUP_SERVER_PID)"

# Aguarda o Chat Engine ficar pronto
sleep 3

# Inicia o Web Gateway em foreground (porta fornecida pelo Render)
echo "Iniciando Web Gateway na porta $PORT..."
python backend/web_gateway.py

exit 0
