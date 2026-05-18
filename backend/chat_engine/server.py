"""
Server - Motor de Chat TCP Puro com Threading Manual.

Implementa o coração do projeto de Sistemas Distribuídos:
- Aceita múltiplas conexões TCP simultâneas
- Instancia explicitamente threading.Thread para cada cliente
- Usa threading.Lock para sincronização thread-safe
- Faz broadcast de mensagens entre clientes

Nenhuma abstração: apenas TCP e concorrência clássica.
"""

import json
import socket
import threading
import logging
from typing import Dict

from runtime_status import write_system_status

from .protocol import (
    HEALTHCHECK_USERNAME,
    validate_username,
    is_http_probe_message,
)

# ============================================================================
# CONFIGURAÇÃO DE LOGGING
# ============================================================================

logger = logging.getLogger(__name__)


# ============================================================================
# CLASSE CHAT ENGINE
# ============================================================================

class ChatEngine:
    """
    Servidor de chat TCP puro com threading manual.

    Responsabilidades Críticas:
    1. Aceitar conexões TCP em um loop infinito.
    2. Para CADA conexão, instanciar UMA threading.Thread.
    3. Usar threading.Lock para sincronizar acesso à lista de clientes.
    4. Fazer broadcast de mensagens de forma thread-safe.

    Conceitos-Chave para o Relatório:
    - Lock (threading.Lock): Previne race conditions no dicionário
      de clientes.
    - Thread (threading.Thread): Permite atender múltiplos clientes
      simultaneamente.
    - Broadcast: Envia mensagem para TODOS os clientes, protegido
      por lock.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 5000,
        server_role: str = "primary",
    ):
        """
        Inicializa o motor do chat.

        Args:
            host: Endereço IP para bind. Usa 127.0.0.1 (localhost)
                  para máxima segurança no ambiente de nuvem.
                  O Gateway se conectará localmente via TCP.
            port: Porta TCP para escuta.
        """
        self.host = host
        self.port = port
        self.server_role = server_role
        self.server_socket = None

        # ===== ESTRUTURA CRÍTICA: Clientes Conectados =====
        # clients = { "username": socket_do_cliente }
        # Este dicionário é acessado por MÚLTIPLAS threads simultaneamente:
        # - Thread A (cliente 1) tenta ler a lista para broadcast.
        # - Thread B (cliente 2) tenta se registrar.
        # Sem lock, há RACE CONDITION: dados corrompem.
        self.clients: Dict[str, socket.socket] = {}
        self.clients_lock = threading.Lock()
        # =====================================================

        self.running = False

    # ========================================================================
    # MÉTODO PRINCIPAL: start() - Loop de Aceitação de Conexões
    # ========================================================================

    def start(self) -> None:
        """
        Inicia o servidor TCP.

        Este método executa o LOOP PRINCIPAL do servidor:
        1. Cria um socket servidor.
        2. Faz bind() e listen().
        3. Entra em um loop infinito que:
           a. Chama accept() (bloqueante até um cliente conectar).
           b. Instancia explicitamente uma threading.Thread.
           c. Chama thread.start() (não espera ela terminar).
           d. Volta para o início do loop (não bloqueado).

        Este é o REQUISITO OBRIGATÓRIO da disciplina:
        "O servidor deve instanciar uma thread para cada conexão."
        Aqui está: threading.Thread(target=self.handle_client, ...).start()
        """
        try:
            # Cria o socket servidor
            self.server_socket = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM
            )
            self.server_socket.setsockopt(
                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1
            )
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)  # Fila de até 5 conexões pendentes

            self.running = True
            write_system_status(
                server_role=self.server_role,
                state="running",
                source="chat_engine",
                engine_host=self.host,
                engine_port=self.port,
            )
            logger.info(
                f"Chat Engine iniciado em {self.host}:{self.port}"
            )

            # ===== LOOP INFINITO DE ACEITAÇÃO =====
            while self.running:
                try:
                    # accept() bloqueia até um cliente conectar.
                    # Retorna: (socket_do_cliente, (IP, PORT))
                    client_socket, client_address = (
                        self.server_socket.accept()
                    )
                    logger.info(
                        f"Nova conexão: {client_address[0]}:{client_address[1]}"
                    )

                    # ===== INSTANCIAÇÃO EXPLÍCITA DE THREAD =====
                    # Esta é a linha mais importante do projeto.
                    # Você vê exatamente a thread sendo criada.
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_address),
                        name=f"ClientThread-{client_address[1]}"
                    )

                    # start() inicia a thread e retorna IMEDIATAMENTE
                    # (não espera handle_client terminar).
                    # Isso permite que o loop volte para accept()
                    # sem bloqueios.
                    client_thread.start()

                    logger.info(
                        f"Thread '{client_thread.name}' iniciada. "
                        f"Total de threads ativas: {threading.active_count()}"
                    )
                    # =============================================

                except Exception as error:
                    if self.running:
                        logger.error(f"Erro ao aceitar conexão: {error}")

        except Exception as error:
            logger.error(f"Erro fatal no servidor: {error}")

        finally:
            self.stop()

    # ========================================================================
    # MÉTODO: handle_client() - Executado em Thread Separada
    # ========================================================================

    def handle_client(
        self,
        client_socket: socket.socket,
        client_address: tuple
    ) -> None:
        """
        Manipula um cliente específico em THREAD SEPARADA.

        Cada cliente tem sua própria thread dedicada:
        - Pode ler dados sem bloquear outras threads.
        - Pode fazer sleep/wait sem afetar o servidor principal.
        - Acessa recursos compartilhados (self.clients) via LOCK.

        Algoritmo:
        1. Recebe o username (primeira mensagem).
        2. Registra o cliente na lista (com lock).
        3. Notifica outros clientes.
        4. Entra em loop: recebe mensagem → broadcast.
        5. Ao desconectar, remove da lista e notifica.

        Args:
            client_socket: Socket TCP do cliente.
            client_address: Tupla (IP, PORT) do cliente.
        """
        username = None
        client_socket.settimeout(1.0)  # Timeout para evitar bloqueios

        try:
            # ===== ETAPA 1: Recebe o username =====
            try:
                data = client_socket.recv(256)
                if not data:
                    logger.warning(
                        f"Conexão de {client_address} fechada "
                        f"antes de fornecer username."
                    )
                    return

                username = (
                    data.decode('utf-8', errors='ignore').strip()
                )
                logger.info(
                    f"Cliente de {client_address} identificou-se "
                    f"como: {username!r}"
                )

                # Ignora healthcheck (usado pelo backup)
                if username == HEALTHCHECK_USERNAME:
                    logger.info(
                        f"Healthcheck recebido de {client_address}; "
                        f"encerrando conexão."
                    )
                    username = None
                    return

                # Ignora probes HTTP e headers que chegam em portas TCP por engano
                if is_http_probe_message(username):
                    logger.info(
                        f"Probe HTTP detectado de {client_address}; "
                        f"desconectando sem entrar no chat."
                    )
                    username = None
                    return

                # Valida o username
                is_valid, error_msg = validate_username(username)
                if not is_valid:
                    logger.warning(
                        f"Username inválido de {client_address}: "
                        f"{username!r} ({error_msg})"
                    )
                    try:
                        client_socket.send(b"Invalid username\n")
                    except Exception:
                        pass
                    return

            except socket.timeout:
                logger.warning(
                    f"Timeout ao esperar username de {client_address}"
                )
                return

            # ===== ETAPA 2: Registra o cliente (COM LOCK) =====
            # Isto é uma SEÇÃO CRÍTICA: múltiplas threads podem
            # tentar registrar clientes simultaneamente.
            # Sem lock, há RACE CONDITION.

            with self.clients_lock:  # Adquire lock
                if username in self.clients:
                    logger.warning(f"Username duplicado: {username}")
                    client_socket.send(b"Username already in use.\n")
                    return

                self.clients[username] = client_socket
                logger.info(
                    f"Cliente registrado: {username}. "
                    f"Total: {len(self.clients)}"
                )
            # LIBERA lock (fim da seção crítica)

            # Notifica outros clientes
            self.broadcast(
                f"[SYSTEM] {username} entrou no chat.",
                exclude=username
            )
            client_socket.send(b"Bem-vindo ao chat!\n")

            system_info = {
                "type": "system_info",
                "thread_id": threading.get_native_id(),
                "thread_name": threading.current_thread().name,
                "server_role": self.server_role,
                "engine_host": self.host,
                "engine_port": self.port,
                "active_clients": len(self.clients),
                "username": username,
            }
            client_socket.send(
                (
                    "__SYSTEM_INFO__ "
                    + json.dumps(system_info, ensure_ascii=False)
                    + "\n"
                ).encode("utf-8")
            )

            # ===== ETAPA 3: Loop de Recepção e Broadcast =====
            while True:
                try:
                    # Recebe mensagem do cliente (até 1024 bytes)
                    data = client_socket.recv(1024)

                    if not data:
                        # Cliente fechou a conexão (FIN packet)
                        logger.info(
                            f"Cliente {username} desconectou (FIN)."
                        )
                        break

                    message = (
                        data.decode('utf-8', errors='ignore').strip()
                    )

                    if not message:
                        continue

                    logger.info(f"Mensagem de {username}: {message}")

                    # Faz broadcast para TODOS os clientes
                    self.broadcast(f"{username}: {message}")

                except socket.timeout:
                    # Timeout é normal; continua tentando
                    continue
                except Exception as error:
                    logger.error(
                        f"Erro ao processar mensagem de {username}: {error}"
                    )
                    break

        except Exception as error:
            logger.error(f"Erro em handle_client ({client_address}): {error}")

        finally:
            # ===== LIMPEZA: Remove cliente (COM LOCK) =====
            if username:
                with self.clients_lock:  # Seção crítica para remoção
                    self.clients.pop(username, None)
                    logger.info(
                        f"Cliente {username} removido. "
                        f"Total: {len(self.clients)}"
                    )

                # Notifica outros clientes
                self.broadcast(f"[SYSTEM] {username} saiu do chat.")

            # Fecha o socket do cliente
            try:
                client_socket.close()
            except Exception:
                pass

            logger.info(f"Thread de {client_address} finalizada.")

    # ========================================================================
    # MÉTODO: broadcast() - Envia Mensagem para Todos
    # ========================================================================

    def broadcast(self, message: str, exclude: str = None) -> None:
        """
        Envia uma mensagem para TODOS os clientes conectados.

        Esta função é chamada por MÚLTIPLAS threads simultaneamente.
        Sem sincronização, self.clients poderia ser modificado
        enquanto iteramos (outra thread desconecta um cliente).

        Solução: Adquirir o lock ANTES de iterar.

        Args:
            message: Mensagem a enviar (string).
            exclude: Username a excluir (para não ecoar para si).
        """
        # Filtra broadcasts de HTTP probes
        if is_http_probe_message(message):
            logger.info(
                f"Ignorando broadcast de probe HTTP: "
                f"{message.splitlines()[0]!r}"
            )
            return

        formatted_message = f"{message}\n".encode('utf-8')

        # Adquire lock E cria uma cópia da lista
        # (liberamos o lock rápido, não ficamos preso durante send())
        with self.clients_lock:
            # Seção crítica: apenas leitura, mas PROTEGIDA
            clients_copy = dict(self.clients)  # Cópia segura

        # Agora enviamos SEM lock (permite que outras threads
        # registrem clientes)
        for username, client_socket in clients_copy.items():
            if exclude and username == exclude:
                continue

            try:
                client_socket.send(formatted_message)
            except Exception as error:
                # Cliente pode estar desconectado; ignora erro
                logger.error(f"Falha ao enviar para {username}: {error}")

    # ========================================================================
    # MÉTODO: stop() - Desliga o Servidor
    # ========================================================================

    def stop(self) -> None:
        """Para o servidor, fecha todas as conexões."""
        self.running = False

        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass

        write_system_status(
            server_role=self.server_role,
            state="stopped",
            source="chat_engine",
            engine_host=self.host,
            engine_port=self.port,
        )

        # Fecha todos os clientes
        with self.clients_lock:
            for username, client_socket in list(self.clients.items()):
                try:
                    client_socket.close()
                except Exception:
                    pass

        logger.info("Chat Engine parado.")
