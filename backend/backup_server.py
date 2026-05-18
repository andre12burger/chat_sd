"""
Backup Server - Monitor ativo-passivo com heartbeat.

Este processo monitora o chat_engine principal por TCP.
Se o principal cair, o backup assume a porta 5000 e sobe um novo ChatEngine.
"""

import logging
import socket
import time
import threading

from chat_engine import ChatEngine
from chat_engine import HEALTHCHECK_USERNAME

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(threadName)s] - %(message)s'
)
logger = logging.getLogger(__name__)


class BackupServer:
    """Servidor de backup com heartbeat e failover automático."""

    def __init__(self, primary_host: str = "127.0.0.1", primary_port: int = 5000, heartbeat_interval: int = 2):
        self.primary_host = primary_host
        self.primary_port = primary_port
        self.heartbeat_interval = heartbeat_interval
        self._failover_started = False

    def _probe_primary(self) -> bool:
        """Tenta conectar ao primário para confirmar que ele está vivo."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe_socket:
                probe_socket.settimeout(1.0)
                probe_socket.connect((self.primary_host, self.primary_port))
                probe_socket.sendall(HEALTHCHECK_USERNAME.encode("utf-8"))
            return True
        except (ConnectionRefusedError, TimeoutError, OSError):
            return False

    def monitor_primary(self) -> None:
        """Monitora continuamente o servidor principal."""
        logger.info("Monitor de backup iniciado")

        while not self._failover_started:
            if self._probe_primary():
                logger.info("Servidor principal OK")
                time.sleep(self.heartbeat_interval)
                continue

            logger.critical("Servidor principal indisponível. Assumindo controle...")
            self.become_primary()
            return

    def become_primary(self) -> None:
        """Sobe um novo ChatEngine na mesma porta do servidor principal."""
        self._failover_started = True
        logger.info("Backup assumindo a porta 5000")

        engine = ChatEngine(host=self.primary_host, port=self.primary_port)
        engine.start()

    def start(self) -> None:
        """Inicia o monitor em uma thread dedicada."""
        monitor_thread = threading.Thread(target=self.monitor_primary, name="BackupMonitor", daemon=False)
        monitor_thread.start()
        monitor_thread.join()


if __name__ == "__main__":
    logger.info("Backup Server iniciado (modo passivo)")
    logger.info("Monitorando servidor principal em 127.0.0.1:5000...")

    backup = BackupServer()

    try:
        backup.start()
    except KeyboardInterrupt:
        logger.info("Backup server parado.")
