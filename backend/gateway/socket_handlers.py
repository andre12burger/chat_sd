"""
Socket Handlers - Eventos SocketIO para Comunicação WebSocket.

Trata eventos do navegador:
- join_chat: Cliente se conecta ao chat
- send_message: Cliente envia mensagem
- disconnect: Cliente desconecta
"""

import logging
import os
from flask import request
from flask_socketio import emit

from runtime_status import read_system_status

from .tcp_proxy import ClientTCPConnection

logger = logging.getLogger(__name__)


# ============================================================================
# MAPEAMENTO GLOBAL: SID -> ClientTCPConnection
# ============================================================================

# Esta estrutura mapeia cada sessão WebSocket (identificada por sid)
# para sua conexão TCP correspondente com o chat_engine.
clients_map = {}
clients_meta = {}


def _get_client_summary(sid: str) -> dict:
    connection = clients_map.get(sid)
    if not connection:
        return {}

    return {
        'sid': sid,
        'username': getattr(connection, 'username', 'desconhecido'),
        'thread_id': getattr(connection, 'thread_id', None),
        'thread_name': getattr(connection, 'thread_name', None),
        'server_role': getattr(connection, 'server_role', None),
        'engine_host': getattr(connection, 'engine_host', None),
        'engine_port': getattr(connection, 'engine_port', None),
    }


def _build_system_state() -> dict:
    status = read_system_status()
    role = status.get('server_role', 'unknown')
    label = 'Primário' if role == 'primary' else 'Backup' if role == 'backup' else 'Indefinido'
    users = [summary for summary in (_get_client_summary(sid) for sid in clients_map.keys()) if summary]
    status.update({
        'server_label': label,
        'active_web_clients': len(clients_map),
        'active_engine_role': role,
        'gateway_pid': os.getpid(),
        'connected_users': users,
    })
    return status


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
        clients_meta[sid] = {
            'username': username,
            'connected_at': tcp_connection.last_system_info.get('connected_at'),
        }

        logger.info(f"[{sid}] Conectado com sucesso ao chat engine")
        system_state = _build_system_state()
        emit(
            'connection_success',
            {
                'username': username,
                'server_role': system_state.get('server_role', 'unknown'),
                'server_label': system_state.get('server_label', 'Indefinido'),
                'active_web_clients': system_state.get('active_web_clients', 0),
            }
        )
        emit('system_state', system_state)
        if tcp_connection.last_system_info:
            emit('system_info', tcp_connection.last_system_info)

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
        clients_meta.pop(sid, None)

        from . import app_context

        socketio = app_context.get_socketio()
        if socketio:
            socketio.emit('system_state', _build_system_state())
