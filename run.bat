@echo off
REM Script de inicialização rápida para Windows (PowerShell/CMD)
REM Usa o caminho direto do Python sem precisar de "conda activate"

cls
echo.
echo ========================================
echo Chat Distribuido - Inicializacao Rapida
echo ========================================
echo.
echo Qual componente deseja iniciar?
echo.
echo [1] Chat Engine (5000)
echo [2] Web Gateway (5001)
echo [3] Ambos (recomendado)
echo.

set /p choice="Digite sua opcao [1-3]: "

REM Caminho direto do Python no ambiente conda
set PYTHON_PATH=C:\Users\andre\miniconda3\envs\chat_sd\python.exe

if "%choice%"=="1" (
    echo Iniciando Chat Engine...
    cmd /k "%PYTHON_PATH% backend/chat_engine.py"
) else if "%choice%"=="2" (
    echo Iniciando Web Gateway...
    cmd /k "%PYTHON_PATH% backend/web_gateway.py"
) else if "%choice%"=="3" (
    echo.
    echo Iniciando ambos os componentes...
    echo [TERMINAL 1] Abrindo Chat Engine
    start cmd /k "title Chat Engine && %PYTHON_PATH% backend/chat_engine.py"
    
    echo Aguardando 3 segundos para o Engine ficar pronto...
    timeout /t 3 /nobreak
    
    echo [TERMINAL 2] Abrindo Web Gateway
    start cmd /k "title Web Gateway && %PYTHON_PATH% backend/web_gateway.py"
    
    echo.
    echo ========================================
    echo Ambos os servicos foram iniciados!
    echo.
    echo Chat Engine: http://127.0.0.1:5000
    echo Web Gateway: http://localhost:5001
    echo.
    echo Abra o navegador em: http://localhost:5001
    echo ========================================
) else (
    echo Opcao invalida. Saindo...
    exit /b 1
)
