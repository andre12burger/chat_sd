"""
Socket Handlers - Eventos SocketIO para Comunicação WebSocket.

Trata eventos do navegador:
- join_chat: Cliente se conecta ao chat
- send_message: Cliente envia mensagem
- disconnect: Cliente desconecta
"""

import logging
from flask_socketio import request, emit

from .tcp_proxy import ClientTCPConnection

logger = logging.getLogger(__name__)


# ============================================================================
# MAPEAMENTO GLOBAL: SID -> ClientTCPConnection
# ============================================================================

# Esta estrutura mapeia cada sessão WebSocket (identificada por sid)
# para sua conexão TCP correspondente com o chat_engine.
clients_map = {}


# ============================================================================
# GERENCIADORES DE MAPA DE CLIENTES
# ============================================================================

def get_client_connection(sid: str) -> ClientTCPConnection:
    """Obtém a conexão TCP de um cliente pelo SID."""
    return clients_map.get(sid)


def register_client_connection(
    sid: str,
    connection: ClientTCPConnection
) -> None:
    """Registra uma nova conexão TCP."""
    clients_map[sid] = connection


def unregister_client_connection(sid: str) -> None:
    """Remove uma conexão TCP."""
    if sid in clients_map:
        del clients_map[sid]


# ============================================================================
# EVENTO: join_chat
# ============================================================================

def on_join_chat(socketio, data):
    """
    Chamado quando um usuário tenta se conectar ao chat.

    Fluxo:
    1. Recebe username do navegador.
    2. Cria uma ClientTCPConnection (abre socket TCP para chat_engine).
    3. Se bem-sucedido, notifica o cliente.
    4. Se falhar, retorna erro.

    Args:
        socketio: Instância do SocketIO.
        data: Dicionário com 'username'.
    """
    sid = request.sid  # Session ID do SocketIO
    username = data.get('username', '').strip()

    logger.info(f"[{sid}] Tentativa de conexão: {username}")

    if not username:
        emit('connection_error', {'error': 'Username inválido'})
        return

    try:
        # Cria a conexão TCP como CLIENTE
        tcp_connection = ClientTCPConnection(sid, username)

        if not tcp_connection.connect():
            emit(
                'connection_error',
                {'error': 'Falha ao conectar ao chat engine'}
            )
            return

        # Registra no mapa global
        register_client_connection(sid, tcp_connection)

        logger.info(f"[{sid}] Conectado com sucesso ao chat engine")
        emit('connection_success', {'username': username})

    except Exception as error:
        logger.error(f"[{sid}] Erro ao processar join_chat: {error}")
        emit('connection_error', {'error': str(error)})


# ============================================================================
# EVENTO: send_message
# ============================================================================

def on_send_message(data):
    """
    Chamado quando o usuário envia uma mensagem via WebSocket.

    Fluxo:
    1. Recupera a conexão TCP do mapa.
    2. Envia a mensagem para o chat_engine via TCP.

    Args:
        data: Dicionário com 'message'.
    """
    sid = request.sid
    message = data.get('message', '').strip()

    if not message:
        return

    tcp_connection = get_client_connection(sid)

    if not tcp_connection:
        logger.warning(f"[{sid}] Tentativa de envio sem conexão")
        emit('connection_error', {'error': 'Não conectado ao chat'})
        return

    tcp_connection.send_to_engine(message)


# ============================================================================
# EVENTO: disconnect
# ============================================================================

def on_disconnect():
    """
    Chamado quando o cliente desconecta.

    Fluxo:
    1. Recupera a conexão TCP.
    2. Desconecta (fecha socket, para thread).
    3. Remove do mapa global.
    """
    sid = request.sid
    logger.info(f"[{sid}] Cliente desconectando")

    tcp_connection = get_client_connection(sid)

    if tcp_connection:
        tcp_connection.disconnect()
        unregister_client_connection(sid)
