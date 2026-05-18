"""
App - Aplicação Flask com SocketIO.

Responsabilidades:
1. Configurar e inicializar Flask + SocketIO.
2. Servir interface HTML/JS/CSS.
3. Registrar rotas estáticas e de saúde.
4. Registrar handlers de eventos SocketIO.
5. Iniciar o servidor web.
"""

import logging
import os
from flask import Flask, send_from_directory
from flask_socketio import SocketIO

from . import socket_handlers
from . import app_context

# ============================================================================
# CONFIGURAÇÃO DE LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(name)s] - %(message)s'
)
logger = logging.getLogger(__name__)

# Reduz verbosidade do Werkzeug (healthchecks, probes)
logging.getLogger('werkzeug').setLevel(logging.WARNING)

# ============================================================================
# CONFIGURAÇÃO FLASK
# ============================================================================

# Cria instância Flask
app = Flask(
    __name__,
    static_folder='../../frontend',
    static_url_path=''
)
app.config['SECRET_KEY'] = 'seu_secret_key_aqui_mudar_em_producao'

# ============================================================================
# CONFIGURAÇÃO SOCKETIO
# ============================================================================

# Força o modo threading no desenvolvimento local.
# Isso evita que o Flask-SocketIO tente usar eventlet automaticamente.
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading"
)

# Define contexto global para que tcp_proxy.py acesse socketio
app_context.set_socketio(socketio)

# ============================================================================
# REGISTRAR HANDLERS SOCKETIO
# ============================================================================

@socketio.on('join_chat')
def on_join_chat_event(data):
    """Wrapper para handler de join_chat."""
    socket_handlers.on_join_chat(socketio, data)


@socketio.on('send_message')
def on_send_message_event(data):
    """Wrapper para handler de send_message."""
    socket_handlers.on_send_message(data)


@socketio.on('disconnect')
def on_disconnect_event():
    """Wrapper para handler de disconnect."""
    socket_handlers.on_disconnect()


# ============================================================================
# ROTAS FLASK - Serviço de Arquivos Estáticos
# ============================================================================

@app.route('/')
def index():
    """Serve o index.html (interface do chat)."""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/health')
def health_check():
    """
    Health check endpoint para Render (e qualquer load balancer).

    Render faz requisições periódicas a este endpoint para confirmar
    que o serviço está vivo. Retorna 200 OK imediatamente.

    Não é logado (silencioso) para não poluir os logs.
    """
    return 'OK', 200


@app.route('/<path:filename>')
def serve_static(filename):
    """Serve arquivos estáticos (CSS, JS, etc)."""
    return send_from_directory(app.static_folder, filename)


# ============================================================================
# ENDPOINT DEMO - Para testar failover
# ============================================================================

@app.route('/demo/kill-engine', methods=['POST'])
def demo_kill_engine():
    """
    [DEMO ONLY] Simula falha do engine matando as conexões TCP.

    Isso permite testar o failover do backup server SEM matar
    todo o serviço. Apenas o engine é "morto", o backup detecta
    e assume.

    Uso:
    - Localmente: curl -X POST http://localhost:10000/demo/kill-engine
    - Render: curl -X POST https://chat-distribuido-m46j.onrender.com/demo/kill-engine
    """
    logger.warning("=" * 60)
    logger.warning(
        "[DEMO] SIMULATING ENGINE FAILURE - Killing all TCP connections"
    )
    logger.warning("=" * 60)

    # Desconecta todos os clientes do engine
    dead_count = 0
    for sid, connection in list(socket_handlers.clients_map.items()):
        try:
            logger.info(f"[DEMO] Closing TCP connection for {sid}")
            connection.disconnect()
            dead_count += 1
        except Exception as error:
            logger.error(f"[DEMO] Error closing {sid}: {error}")

    logger.warning(
        f"[DEMO] Killed {dead_count} connections. "
        f"Backup should take over in ~2 seconds."
    )
    logger.warning("=" * 60)

    return {
        "status": "ok",
        "message": (
            f"Simulated engine failure. Killed {dead_count} TCP "
            f"connections. Backup should assume control in ~2 seconds."
        ),
    }, 200


# ============================================================================
# PONTO DE ENTRADA
# ============================================================================

def run_app():
    """Inicia a aplicação web."""
    logger.info("=" * 60)
    logger.info("Web Gateway iniciando...")
    logger.info("=" * 60)
    logger.info(
        "Certifique-se de que o chat_engine.py está "
        "rodando em localhost:5000"
    )

    # Para desenvolvimento local, usa port 5001.
    # Para deploy no Render.com, usa variável de ambiente PORT.
    port = int(os.environ.get('PORT', 5001))
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'

    logger.info(f"Abra http://localhost:{port} no navegador")
    logger.info("=" * 60)

    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        debug=debug_mode,
        use_reloader=False,
        allow_unsafe_werkzeug=True
    )


if __name__ == "__main__":
    run_app()
