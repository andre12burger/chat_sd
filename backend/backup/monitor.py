"""
Monitor - Servidor de Backup com Heartbeat e Failover Automático.

Este processo monitora o chat_engine principal por TCP.
Se o principal cair, o backup assume a porta 5000 e sobe um novo ChatEngine.
"""

import logging
import socket
import time
import threading
from datetime import datetime, timezone

from chat_engine import ChatEngine, HEALTHCHECK_USERNAME
from runtime_status import write_system_status

# ============================================================================
# CONFIGURAÇÃO DE LOGGING
# ============================================================================

logger = logging.getLogger(__name__)


# ============================================================================
# CLASSE BACKUP SERVER
# ============================================================================

class BackupServer:
    """
    Servidor de backup com heartbeat e failover automático.

    Responsabilidades:
    1. Conectar ao servidor principal periodicamente (heartbeat).
    2. Detectar falha quando a conexão é recusada/timeout.
    3. Assumir o controle ligando um novo ChatEngine na mesma porta.
    """

    def __init__(
        self,
        primary_host: str = "127.0.0.1",
        primary_port: int = 5000,
        heartbeat_interval: int = 2
    ):
        """
        Inicializa o backup server.

        Args:
            primary_host: Host do servidor principal.
            primary_port: Porta do servidor principal.
            heartbeat_interval: Intervalo (segundos) entre heartbeats.
        """
        self.primary_host = primary_host
        self.primary_port = primary_port
        self.heartbeat_interval = heartbeat_interval
        self._failover_started = False

    # ========================================================================
    # MÉTODO: _probe_primary() - Verifica se o Primário está Vivo
    # ========================================================================

    def _probe_primary(self) -> bool:
        """
        Tenta conectar ao primário para confirmar que ele está vivo.

        Envia o username especial HEALTHCHECK_USERNAME para identificar
        a conexão como um probe (não um cliente normal).

        Returns:
            True se o primário respondeu, False se desconectado/timeout.
        """
        try:
            with socket.socket(
                socket.AF_INET, socket.SOCK_STREAM
            ) as probe_socket:
                probe_socket.settimeout(1.0)
                probe_socket.connect(
                    (self.primary_host, self.primary_port)
                )
                probe_socket.sendall(
                    HEALTHCHECK_USERNAME.encode("utf-8")
                )
            return True
        except (
            ConnectionRefusedError, TimeoutError, OSError
        ):
            return False

    # ========================================================================
    # MÉTODO: monitor_primary() - Loop de Monitoramento
    # ========================================================================

    def monitor_primary(self) -> None:
        """
        Monitora continuamente o servidor principal.

        Algoritmo:
        1. Faz heartbeat a cada N segundos.
        2. Se bem-sucedido, continua monitorando.
        3. Se falhar, assume o controle (failover).
        """
        logger.info("Monitor de backup iniciado")

        while not self._failover_started:
            if self._probe_primary():
                logger.info("Servidor principal OK")
                time.sleep(self.heartbeat_interval)
                continue

            logger.critical(
                "Servidor principal indisponível. "
                "Assumindo controle..."
            )
            self.become_primary()
            return

    # ========================================================================
    # MÉTODO: become_primary() - Assume o Controle
    # ========================================================================

    def become_primary(self) -> None:
        """
        Sobe um novo ChatEngine na mesma porta do servidor principal.

        Este é o momento do failover:
        - O backup se torna o primário.
        - Clientes conectados ao engine antigo podem reconectar.
        - O gateway detecta a falha e reconecta automaticamente.
        """
        self._failover_started = True
        write_system_status(
            server_role="backup",
            state="failover",
            source="backup_server",
            engine_host=self.primary_host,
            engine_port=self.primary_port,
            last_failover_reason="Heartbeat do primário falhou",
            last_failover_at=datetime.now(timezone.utc).isoformat(),
        )
        logger.info(
            f"Backup assumindo a porta {self.primary_port}"
        )

        engine = ChatEngine(
            host=self.primary_host,
            port=self.primary_port,
            server_role="backup",
        )
        engine.start()

    # ========================================================================
    # MÉTODO: start() - Inicia o Monitor
    # ========================================================================

    def start(self) -> None:
        """
        Inicia o monitor em uma thread dedicada.

        O monitor roda indefinidamente até um failover.
        """
        monitor_thread = threading.Thread(
            target=self.monitor_primary,
            name="BackupMonitor",
            daemon=False
        )
        monitor_thread.start()
        monitor_thread.join()
