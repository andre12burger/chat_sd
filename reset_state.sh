#!/bin/bash
# Script para resetar o estado do sistema antes de uma apresentação
# Uso: ./reset_state.sh

echo "🔄 Resetando estado do sistema..."

STATUS_FILE="backend/.runtime/system_status.json"

if [ -f "$STATUS_FILE" ]; then
    rm "$STATUS_FILE"
    echo "✅ Arquivo de estado removido: $STATUS_FILE"
else
    echo "ℹ️  Arquivo de estado não existe (OK)"
fi

echo ""
echo "📋 Próximas etapas:"
echo "  1. Terminal 1: python backend/chat_engine.py"
echo "  2. Terminal 2: python backend/backup_server.py"
echo "  3. Terminal 3: python backend/web_gateway.py"
echo "  4. Abra http://localhost:5001 no navegador"
echo "  5. Conecte com username 'andre'"
echo "  6. Verifique que Status = PRIMARY ✅"
echo "  7. Agora você pode rodar o teste de failover!"
echo ""
