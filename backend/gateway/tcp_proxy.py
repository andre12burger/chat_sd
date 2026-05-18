"""
TCP Proxy - Gerenciador de Conexão TCP com Chat Engine.

Encapsula:
- Conexão TCP como cliente para o chat_engine
- Thread background que lê mensagens do Engine
- Métodos para enviar e receber
- Reconexão automática com retry
"""

import socket
import threading
import logging
import os
import time

logger = logging.getLogger(__name__)


# ============================================================================
# CLASSE CLIENT TCP CONNECTION
# ============================================================================

class ClientTCPConnection:
    """
    Representa a conexão TCP de um cliente WebSocket com o chat_engine.

    Esta classe encapsula:
    - A conexão TCP em si (socket).
    - A thread background que lê mensagens do Engine.
    - Métodos para enviar e receber.
    - Reconexão automática com handshake de autenticação.
    """

    def __init__(
        self,
        sid: str,
        username: str,
        engine_host: str = None,
        engine_port: int = None
    ):
        """
        Inicializa a conexão TCP.

        Args:
            sid: Session ID do SocketIO (identifica cliente web).
            username: Nome de usuário.
            engine_host: Host do chat_engine (padrão: variável ambiente).
            engine_port: Porta do chat_engine (padrão: variável ambiente).
        """
        self.sid = sid
        self.username = username
        self.engine_host = (
            engine_host or os.environ.get("ENGINE_HOST", "127.0.0.1")
        )
        self.engine_port = (
            engine_port or int(os.environ.get("ENGINE_PORT", "5000"))
        )
        self.connect_retries = int(
            os.environ.get("ENGINE_CONNECT_RETRIES", "5")
        )
        self.connect_retry_delay = float(
            os.environ.get("ENGINE_CONNECT_RETRY_DELAY", "1.0")
        )

        self.tcp_socket = None
        self.reader_thread = None
        self.connected = False
        self.authenticated = False  # ← Novo: flag de autenticação
        self.auth_event = threading.Event()  # ← Novo: sincronização

    # ========================================================================
    # MÉTODO: connect() - Abre Conexão TCP e Dispara Thread de Leitura
    # ========================================================================

    def connect(self) -> bool:
        """
        Abre a conexão TCP com o chat_engine e dispara thread de leitura.

        Handshake:
        1. Conecta ao engine.
        2. Envia username.
        3. Aguarda confirmação "Bem-vindo ao chat!" (gerenciado por _read_from_engine).

        Retorna:
            True se conectado com sucesso, False caso contrário.
        """
        try:
            last_error = None
            
            # Reseta flags de autenticação para nova tentativa
            self.authenticated = False
            self.auth_event.clear()

            for attempt in range(1, self.connect_retries + 1):
                try:
                    # Cria socket TCP como CLIENTE
                    self.tcp_socket = socket.socket(
                        socket.AF_INET, socket.SOCK_STREAM
                    )
                    self.tcp_socket.settimeout(5.0)

                    # Conecta ao chat_engine
                    self.tcp_socket.connect(
                        (self.engine_host, self.engine_port)
                    )
                    logger.info(
                        f"[{self.sid}] Conectado ao chat_engine "
                        f"({self.engine_host}:{self.engine_port})"
                    )

                    # Envia username como primeira mensagem com NEWLINE
                    # para separar do próximo
                    self.tcp_socket.send(
                        (self.username + '\n').encode('utf-8')
                    )

                    self.connected = True

                    # ===== DISPARA THREAD DE LEITURA EM BACKGROUND =====
                    # Esta thread ficará esperando mensagens do
                    # chat_engine. Primeiro message deve ser
                    # "Bem-vindo ao chat!" para confirmar autenticação.
                    self.reader_thread = threading.Thread(
                        target=self._read_from_engine,
                        daemon=True,
                        name=f"TCPReader-{self.sid}"
                    )
                    self.reader_thread.start()
                    logger.info(
                        f"[{self.sid}] Thread de leitura iniciada "
                        f"({self.reader_thread.name})"
                    )

                    return True

                except Exception as error:
                    last_error = error
                    logger.warning(
                        f"[{self.sid}] Tentativa {attempt}/"
                        f"{self.connect_retries} falhou ao conectar "
                        f"ao chat_engine: {error}"
                    )
                    self.disconnect()

                    if attempt < self.connect_retries:
                        time.sleep(self.connect_retry_delay)

            logger.error(
                f"[{self.sid}] Não foi possível conectar ao "
                f"chat_engine após {self.connect_retries} tentativas: "
                f"{last_error}"
            )
            return False

        except Exception as error:
            logger.error(
                f"[{self.sid}] Erro ao conectar ao chat_engine: {error}"
            )
            self.disconnect()
            return False

    # ========================================================================
    # MÉTODO: _read_from_engine() - Thread Background
    # ========================================================================

    def _read_from_engine(self) -> None:
        """
        Thread background: lê mensagens do chat_engine.

        Detecta:
        - "Bem-vindo ao chat!" → Sinal de autenticação bem-sucedida
        - Mensagens normais → Repassar ao navegador
        - Erros → Desconectar
        """
        first_message = True
        try:
            while self.connected:
                try:
                    # Bloqueia esperando dados do chat_engine
                    data = self.tcp_socket.recv(1024)

                    if not data:
                        # Chat_engine fechou (FIN)
                        logger.info(
                            f"[{self.sid}] Chat Engine desconectou"
                        )
                        break

                    message = (
                        data.decode('utf-8', errors='ignore').strip()
                    )

                    if message:
                        logger.info(
                            f"[{self.sid}] Recebido do Engine: {message}"
                        )
                        
                        # ===== DETECTA CONFIRMAÇÃO DE AUTENTICAÇÃO =====
                        # Primeira mensagem do engine deve ser "Bem-vindo ao chat!"
                        if first_message:
                            first_message = False
                            if "Bem-vindo ao chat" in message:
                                self.authenticated = True
                                self.auth_event.set()
                                logger.info(
                                    f"[{self.sid}] Autenticação confirmada pelo Engine"
                                )
                                continue  # Não emite para o navegador
                            else:
                                logger.error(
                                    f"[{self.sid}] Erro na autenticação: {message}"
                                )
                                break
                        
                        # Ignora mensagens de probe HTTP
                        if (
                            'HTTP/' in message
                            or message.startswith('HEAD ')
                            or message.startswith('GET ')
                        ):
                            logger.info(
                                f"[{self.sid}] Ignorando probe HTTP: "
                                f"{message.splitlines()[0]!r}"
                            )
                            continue

                        # ===== EMITE PARA NAVEGADOR VIA WEBSOCKET =====
                        # Importamos aqui para evitar circular import
                        from . import app_context
                        socketio = app_context.get_socketio()
                        if socketio:
                            socketio.emit(
                                'receive_message',
                                {'message': message},
                                room=self.sid
                            )

                except socket.timeout:
                    # Timeout é normal; continua tentando
                    continue
                except Exception as error:
                    logger.error(
                        f"[{self.sid}] Erro ao ler do Engine: {error}"
                    )
                    break

        finally:
            self.disconnect()

    # ========================================================================
    # MÉTODO: send_to_engine() - Envia Mensagem para Chat Engine
    # ========================================================================

    def send_to_engine(self, message: str) -> bool:
        """
        Envia uma mensagem para o chat_engine via TCP.

        Aguarda autenticação antes de enviar (sincronização).

        Args:
            message: Mensagem a enviar.

        Returns:
            True se enviado com sucesso, False caso contrário.
        """
        if not self.connected or not self.tcp_socket:
            logger.warning(
                f"[{self.sid}] Socket desconectado; tentando "
                f"reconectar antes de enviar"
            )
            if not self.connect():
                return False

        # ===== AGUARDA AUTENTICAÇÃO =====
        # Espera até 5 segundos pela confirmação do engine
        if not self.authenticated:
            logger.info(
                f"[{self.sid}] Aguardando autenticação antes de enviar..."
            )
            if not self.auth_event.wait(timeout=5.0):
                logger.error(
                    f"[{self.sid}] Timeout aguardando autenticação"
                )
                self.disconnect()
                return False

        try:
            self.tcp_socket.send((message + '\n').encode('utf-8'))
            logger.info(
                f"[{self.sid}] Enviado para Engine: {message}"
            )
            return True
        except Exception as error:
            logger.error(
                f"[{self.sid}] Erro ao enviar para Engine: {error}"
            )
            self.disconnect()
            if self.connect():
                # ===== AGUARDA AUTENTICAÇÃO NOVAMENTE =====
                if not self.authenticated:
                    if not self.auth_event.wait(timeout=5.0):
                        logger.error(
                            f"[{self.sid}] Timeout na reconexão"
                        )
                        self.disconnect()
                        return False
                
                try:
                    self.tcp_socket.send(
                        (message + '\n').encode('utf-8')
                    )
                    logger.info(
                        f"[{self.sid}] Enviado para Engine "
                        f"após reconexão: {message}"
                    )
                    return True
                except Exception as retry_error:
                    logger.error(
                        f"[{self.sid}] Falha ao reenviar "
                        f"após reconexão: {retry_error}"
                    )
                    self.disconnect()
            return False

    # ========================================================================
    # MÉTODO: disconnect() - Fecha Conexão TCP
    # ========================================================================

    def disconnect(self) -> None:
        """Fecha a conexão TCP e libera recursos."""
        self.connected = False
        self.authenticated = False
        self.auth_event.clear()

        if self.tcp_socket:
            try:
                self.tcp_socket.close()
            except Exception:
                pass

        logger.info(f"[{self.sid}] Desconectado do chat_engine")
