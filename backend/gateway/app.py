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
import threading
import time
from flask import Flask, send_from_directory
from flask_socketio import SocketIO

from . import socket_handlers
from . import app_context
from runtime_status import read_system_status

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

_monitor_started = False
_last_state_signature = None
_last_server_role = None

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


def _build_system_state_snapshot():
    status = read_system_status()
    role = status.get('server_role', 'unknown')
    label = 'Primário' if role == 'primary' else 'Backup' if role == 'backup' else 'Indefinido'
    status.update({
        'server_role': role,
        'server_label': label,
        'active_web_clients': len(socket_handlers.clients_map),
        'cpu_threads': os.cpu_count() or 1,
    })
    return status


def _system_monitor_loop():
    global _last_state_signature, _last_server_role

    while True:
        snapshot = _build_system_state_snapshot()
        signature = (
            snapshot.get('server_role'),
            snapshot.get('state'),
            snapshot.get('active_web_clients'),
        )

        if signature != _last_state_signature:
            socketio.emit('system_state', snapshot)

            if _last_server_role is not None and snapshot.get('server_role') != _last_server_role:
                socketio.emit('server_change', {
                    'server_role': snapshot.get('server_role', 'unknown'),
                    'server_label': snapshot.get('server_label', 'Indefinido'),
                    'state': snapshot.get('state', 'unknown'),
                    'message': (
                        'Servidor backup assumiu o controle.'
                        if snapshot.get('server_role') == 'backup'
                        else 'Servidor primário voltou ao ar.'
                    ),
                })

            _last_state_signature = signature
            _last_server_role = snapshot.get('server_role')

        time.sleep(2.0)


def start_system_monitor():
    global _monitor_started
    if _monitor_started:
        return

    monitor_thread = threading.Thread(
        target=_system_monitor_loop,
        name='SystemMonitor',
        daemon=True,
    )
    monitor_thread.start()
    _monitor_started = True


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

    start_system_monitor()

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
