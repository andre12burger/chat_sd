"""
App Context - Contexto global da aplicação.

Fornece acesso à instância de SocketIO para módulos que precisam.
Evita circular imports.
"""

_socketio = None


def set_socketio(socketio_instance):
    """Define a instância global de SocketIO."""
    global _socketio
    _socketio = socketio_instance


def get_socketio():
    """Retorna a instância global de SocketIO."""
    return _socketio
