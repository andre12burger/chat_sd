"""
Chat Engine Package - Motor de Chat TCP Puro com Threading Manual.

Exporta:
- ChatEngine: Servidor TCP com múltiplos clientes
- HEALTHCHECK_USERNAME: Username reservado para heartbeat
- validate_username: Função de validação
- is_http_probe_message: Detector de probes HTTP
"""

from .server import ChatEngine
from .protocol import (
    HEALTHCHECK_USERNAME,
    validate_username,
    is_http_probe_message,
)

__all__ = [
    'ChatEngine',
    'HEALTHCHECK_USERNAME',
    'validate_username',
    'is_http_probe_message',
]
