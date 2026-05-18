# Script para resetar o estado do sistema antes de uma apresentação
# Uso: .\reset_state.ps1

Write-Host "🔄 Resetando estado do sistema..." -ForegroundColor Cyan

$statusFile = "backend\.runtime\system_status.json"

if (Test-Path $statusFile) {
    Remove-Item $statusFile -Force
    Write-Host "✅ Arquivo de estado removido: $statusFile" -ForegroundColor Green
} else {
    Write-Host "ℹ️  Arquivo de estado não existe (OK)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "📋 Próximas etapas:" -ForegroundColor Cyan
Write-Host "  1. Terminal 1: python backend/chat_engine.py" -ForegroundColor White
Write-Host "  2. Terminal 2: python backend/backup_server.py" -ForegroundColor White
Write-Host "  3. Terminal 3: python backend/web_gateway.py" -ForegroundColor White
Write-Host "  4. Abra http://localhost:5001 no navegador" -ForegroundColor White
Write-Host "  5. Conecte com username 'andre'" -ForegroundColor White
Write-Host "  6. Verifique que Status = PRIMARY ✅" -ForegroundColor White
Write-Host "  7. Agora você pode rodar o teste de failover!" -ForegroundColor Green
Write-Host ""
