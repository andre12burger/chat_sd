# Script para usar o ambiente conda sem "conda activate"
# Útil quando conda init não está totalmente funcional

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Chat_SD - Ambiente Conda" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# Caminho direto do Python no ambiente conda
$pythonPath = "C:\Users\andre\miniconda3\envs\chat_sd\python.exe"

# Verificar se Python existe
if (-Not (Test-Path $pythonPath)) {
    Write-Host "✗ ERRO: Python não encontrado em $pythonPath" -ForegroundColor Red
    Write-Host "Verifique se o ambiente 'chat_sd' foi criado corretamente." -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ Python encontrado: $pythonPath" -ForegroundColor Green
Write-Host ""
Write-Host "Agora você pode executar:" -ForegroundColor Cyan
Write-Host "  Terminal 1: & '$pythonPath' backend/chat_engine.py" -ForegroundColor White
Write-Host "  Terminal 2: & '$pythonPath' backend/web_gateway.py" -ForegroundColor White
Write-Host ""
Write-Host "Ou use o script run.bat para inicializar automaticamente." -ForegroundColor Yellow
