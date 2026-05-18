# Script PowerShell para iniciar Chat Engine e Web Gateway
# Sem dependência de "conda activate"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Chat Distribuido - Inicialização" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Caminho direto do Python
$pythonPath = "C:\Users\andre\miniconda3\envs\chat_sd\python.exe"

# Verificar se existe
if (-Not (Test-Path $pythonPath)) {
    Write-Host "✗ ERRO: Python não encontrado!" -ForegroundColor Red
    Write-Host "   Caminho: $pythonPath" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ Python encontrado: $pythonPath" -ForegroundColor Green
Write-Host ""

# Menu
Write-Host "Qual componente iniciar?" -ForegroundColor Yellow
Write-Host "[1] Chat Engine (porta 5000)" -ForegroundColor White
Write-Host "[2] Web Gateway (porta 5001)" -ForegroundColor White
Write-Host "[3] Ambos (RECOMENDADO)" -ForegroundColor Cyan
Write-Host ""

$choice = Read-Host "Digite [1-3]"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "Iniciando Chat Engine..." -ForegroundColor Green
        & $pythonPath backend/chat_engine.py
    }
    "2" {
        Write-Host ""
        Write-Host "Iniciando Web Gateway..." -ForegroundColor Green
        & $pythonPath backend/web_gateway.py
    }
    "3" {
        Write-Host ""
        Write-Host "Iniciando AMBOS os serviços..." -ForegroundColor Green
        Write-Host ""
        
        Write-Host "[1/2] Abrindo Chat Engine..." -ForegroundColor Cyan
        Start-Process powershell -ArgumentList "-Command", "& '$pythonPath' backend/chat_engine.py" -WindowStyle Normal
        
        Write-Host "Aguardando 3 segundos..." -ForegroundColor Yellow
        Start-Sleep -Seconds 3
        
        Write-Host "[2/2] Abrindo Web Gateway..." -ForegroundColor Cyan
        Start-Process powershell -ArgumentList "-Command", "& '$pythonPath' backend/web_gateway.py" -WindowStyle Normal
        
        Write-Host ""
        Write-Host "=========================================" -ForegroundColor Green
        Write-Host "✓ Ambos os serviços iniciados!" -ForegroundColor Green
        Write-Host "=========================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Abra no navegador:" -ForegroundColor Cyan
        Write-Host "  http://localhost:5001" -ForegroundColor White
        Write-Host ""
        Write-Host "Abra 3+ abas e teste com nomes:" -ForegroundColor Yellow
        Write-Host "  alice, bob, charlie" -ForegroundColor White
        Write-Host ""
    }
    default {
        Write-Host "✗ Opção inválida!" -ForegroundColor Red
        exit 1
    }
}
