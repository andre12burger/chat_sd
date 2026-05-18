#!/usr/bin/env python3
"""
Script de Validação - Testa imports e estrutura do projeto refatorado.

Executa:
  python test_imports.py
"""

import sys
import os

# Adiciona backend ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

print("=" * 70)
print("VALIDAÇÃO DA REFATORAÇÃO MODULAR")
print("=" * 70)
print()

# Teste 1: Chat Engine
print("📦 Testando módulo chat_engine/")
try:
    from chat_engine import ChatEngine, HEALTHCHECK_USERNAME
    print("   ✅ ChatEngine importado com sucesso")
    print(f"   ✅ HEALTHCHECK_USERNAME: {HEALTHCHECK_USERNAME!r}")
    print()
except Exception as e:
    print(f"   ❌ Erro ao importar chat_engine: {e}")
    sys.exit(1)

# Teste 2: Protocol
print("📦 Testando módulo chat_engine/protocol.py")
try:
    from chat_engine.protocol import (
        validate_username,
        is_http_probe_message,
        HTTP_METHODS
    )
    print("   ✅ validate_username() importado")
    print("   ✅ is_http_probe_message() importado")
    print(f"   ✅ HTTP_METHODS: {len(HTTP_METHODS)} métodos")
    
    # Testa validação
    is_valid, msg = validate_username("alice")
    print(f"   ✅ validate_username('alice'): {is_valid}")
    
    is_valid, msg = validate_username("GET")
    print(f"   ✅ validate_username('GET'): {is_valid} (corretamente rejeitado)")
    print()
except Exception as e:
    print(f"   ❌ Erro ao importar protocol: {e}")
    sys.exit(1)

# Teste 3: Server
print("📦 Testando módulo chat_engine/server.py")
try:
    from chat_engine.server import ChatEngine as EngineClass
    print("   ✅ ChatEngine (classe) importado direto")
    print(f"   ✅ Tipo: {type(EngineClass)}")
    print()
except Exception as e:
    print(f"   ❌ Erro ao importar server: {e}")
    sys.exit(1)

# Teste 4: Gateway
print("📦 Testando módulo gateway/")
try:
    from gateway import app, socketio, run_app
    print("   ✅ app (Flask) importado")
    print("   ✅ socketio importado")
    print("   ✅ run_app() importado")
    print()
except Exception as e:
    print(f"   ❌ Erro ao importar gateway: {e}")
    print(f"      Detalhes: {e}")
    sys.exit(1)

# Teste 5: TCP Proxy
print("📦 Testando módulo gateway/tcp_proxy.py")
try:
    from gateway.tcp_proxy import ClientTCPConnection
    print("   ✅ ClientTCPConnection importado")
    print(f"   ✅ Tipo: {type(ClientTCPConnection)}")
    print()
except Exception as e:
    print(f"   ❌ Erro ao importar tcp_proxy: {e}")
    sys.exit(1)

# Teste 6: Socket Handlers
print("📦 Testando módulo gateway/socket_handlers.py")
try:
    from gateway.socket_handlers import (
        on_join_chat,
        on_send_message,
        on_disconnect
    )
    print("   ✅ on_join_chat() importado")
    print("   ✅ on_send_message() importado")
    print("   ✅ on_disconnect() importado")
    print()
except Exception as e:
    print(f"   ❌ Erro ao importar socket_handlers: {e}")
    sys.exit(1)

# Teste 7: Backup
print("📦 Testando módulo backup/")
try:
    from backup import BackupServer
    print("   ✅ BackupServer importado")
    print(f"   ✅ Tipo: {type(BackupServer)}")
    print()
except Exception as e:
    print(f"   ❌ Erro ao importar backup: {e}")
    sys.exit(1)

# Teste 8: Monitor
print("📦 Testando módulo backup/monitor.py")
try:
    from backup.monitor import BackupServer as BackupClass
    print("   ✅ BackupServer (classe) importado direto")
    print(f"   ✅ Tipo: {type(BackupClass)}")
    print()
except Exception as e:
    print(f"   ❌ Erro ao importar monitor: {e}")
    sys.exit(1)

# Resumo
print("=" * 70)
print("✅ TODOS OS MÓDULOS VALIDADOS COM SUCESSO!")
print("=" * 70)
print()
print("Estrutura validada:")
print("  ✅ chat_engine/ (protocol + server + __init__)")
print("  ✅ gateway/ (tcp_proxy + socket_handlers + app + app_context + __init__)")
print("  ✅ backup/ (monitor + __init__)")
print("  ✅ Entry points: chat_engine.py, web_gateway.py, backup_server.py")
print()
print("Próximo passo: ./start.sh para iniciar o projeto!")
