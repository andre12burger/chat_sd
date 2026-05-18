#!/bin/bash

# Start Script para Deploy no Render.com
# Este script inicia o Chat Engine em background e o Web Gateway em foreground

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

# Aguarda o Chat Engine ficar pronto
sleep 3

# Inicia o Web Gateway em foreground (porta fornecida pelo Render)
echo "Iniciando Web Gateway na porta $PORT..."
python backend/web_gateway.py

# Se o Web Gateway terminar, encerra o Chat Engine também
echo "Web Gateway finalizado. Encerrando Chat Engine..."
kill $CHAT_ENGINE_PID 2>/dev/null

exit 0
