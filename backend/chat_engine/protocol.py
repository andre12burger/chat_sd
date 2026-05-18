"""
Protocol - Constantes e Validações do Chat TCP.

Centraliza:
- Constantes do protocolo (usernames especiais)
- Funções de validação de username
- Definições de mensagens do sistema
"""

import re
from typing import Tuple

# ============================================================================
# CONSTANTES DO PROTOCOLO
# ============================================================================

HEALTHCHECK_USERNAME = "__healthcheck__"
"""Username especial usado pelo backup server para heartbeat."""

HTTP_METHODS = {
    "GET", "POST", "HEAD", "PUT", "DELETE",
    "OPTIONS", "TRACE", "CONNECT", "PATCH"
}
"""Métodos HTTP que não são usernames válidos (proteção contra probes)."""


# ============================================================================
# FUNÇÕES DE VALIDAÇÃO
# ============================================================================

def validate_username(username: str) -> Tuple[bool, str]:
    """
    Valida um username conforme o protocolo do chat.

    Regras de validação:
    1. Comprimento: 1-20 caracteres.
    2. Caracteres permitidos: a-z, A-Z, 0-9, _, -
    3. Não é um método HTTP (GET, POST, etc).
    4. Não é o username reservado do healthcheck.

    Args:
        username: Username a validar.

    Returns:
        Tupla (válido, mensagem_erro).
        Se válido: (True, "")
        Se inválido: (False, "motivo")
    """
    if not username:
        return False, "Username não pode estar vazio."

    # Verifica comprimento
    if not (1 <= len(username) <= 20):
        return False, "Username deve ter 1-20 caracteres."

    # Verifica caracteres permitidos
    if not re.match(r'^[A-Za-z0-9_\-]{1,20}$', username):
        return False, (
            "Username deve conter apenas letras, números, underscore (_) e hífen (-)."
        )

    # Verifica se é método HTTP
    if username.upper() in HTTP_METHODS:
        return False, f"Username '{username}' não é permitido (parece método HTTP)."

    # Verifica se é username reservado (healthcheck)
    if username == HEALTHCHECK_USERNAME:
        return False, f"Username '{username}' é reservado para o sistema."

    return True, ""


def is_http_probe_message(message: str) -> bool:
    """
    Detecta se uma mensagem parece ser um probe HTTP.

    Probes HTTP vêm de healthchecks e monitores.
    Exemplo: "GET / HTTP/1.1"

    Args:
        message: Mensagem a verificar.

    Returns:
        True se parece probe HTTP, False caso contrário.
    """
    if not isinstance(message, str):
        return False

    # Detecta padrões típicos de HTTP
    http_indicators = ('HTTP/', 'GET ', 'HEAD ', 'POST ', 'PUT ', 'DELETE ')
    return any(message.startswith(indicator) for indicator in http_indicators)
