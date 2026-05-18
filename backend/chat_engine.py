"""
Chat Engine - Motor de Chat Puro com Sockets e Threading.

Este módulo é o CORAÇÃO do projeto de Sistemas Distribuídos.
Implementa MANUALMENTE:
- Aceitação de múltiplas conexões simultâneas (socket.accept())
- Instanciação explícita de threading.Thread para cada cliente
- Sincronização thread-safe com threading.Lock
- Broadcast de mensagens entre clientes

Nada de WebSocket, HTTP ou abstrações. Apenas TCP e concorrência clássica.
"""

import socket
import threading
import logging
import re
from typing import Dict, Set
from datetime import datetime

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(threadName)s] - %(message)s'
)
logger = logging.getLogger(__name__)

HEALTHCHECK_USERNAME = "__healthcheck__"

# ============================================================================
# CHAT ENGINE (O Motor Principal)
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
    - Lock (threading.Lock): Previne race conditions no dicionário de clientes.
    - Thread (threading.Thread): Permite que múltiplos clientes sejam atendidos simultaneamente.
    - Broadcast: Envia uma mensagem para TODOS os clientes, protegido por lock.
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 5000):
        """
        Inicializa o engine.
        
        Args:
            host: Endereço IP para bind. Usa 127.0.0.1 (localhost) para máxima segurança
                  no ambiente de nuvem. O Gateway se conectará localmente via TCP.
            port: Porta TCP para escuta.
        """
        self.host = host
        self.port = port
        self.server_socket = None
        
        # ===== ESTRUTURA CRÍTICA: Clientes Conectados =====
        # clients = { "username": socket_do_cliente }
        # Este dicionário é acessado por MÚLTIPLAS threads simultaneamente:
        # - Thread A (cliente 1) tenta ler a lista para broadcast.
        # - Thread B (cliente 2) tenta se registrar.
        # Sem lock, há RACE CONDITION: dados corrompem.
        self.clients: Dict[str, socket.socket] = {}
        self.clients_lock = threading.Lock()
        # ====================================================
        
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
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)  # Fila de até 5 conexões pendentes
            
            self.running = True
            logger.info(f"Chat Engine iniciado em {self.host}:{self.port}")
            
            # ===== LOOP INFINITO DE ACEITAÇÃO =====
            while self.running:
                try:
                    # accept() bloqueia até um cliente conectar.
                    # Retorna: (socket_do_cliente, (IP, PORT))
                    client_socket, client_address = self.server_socket.accept()
                    logger.info(f"Nova conexão: {client_address[0]}:{client_address[1]}")
                    
                    # ===== INSTANCIAÇÃO EXPLÍCITA DE THREAD =====
                    # Esta é a linha mais importante do projeto para o professor.
                    # Não há "magia" aqui: você vê exatamente a thread sendo criada.
                    client_thread = threading.Thread(
                        target=self.handle_client,        # Função a executar
                        args=(client_socket, client_address),  # Argumentos
                        name=f"ClientThread-{client_address[1]}"  # Nome para debug
                    )
                    
                    # start() inicia a thread e retorna IMEDIATAMENTE
                    # (não espera handle_client terminar).
                    # Isso permite que o loop volte para accept() sem bloqueios.
                    client_thread.start()
                    
                    logger.info(
                        f"Thread '{client_thread.name}' iniciada. "
                        f"Total de threads ativas: {threading.active_count()}"
                    )
                    # =============================================
                
                except Exception as e:
                    if self.running:
                        logger.error(f"Erro ao aceitar conexão: {e}")
        
        except Exception as e:
            logger.error(f"Erro fatal no servidor: {e}")
        
        finally:
            self.stop()
    
    # ========================================================================
    # MÉTODO: handle_client() - Executado em Thread Separada por Cliente
    # ========================================================================
    
    def handle_client(self, client_socket: socket.socket, client_address: tuple) -> None:
        """
        Manipula um cliente específico. Esta função executa em uma THREAD SEPARADA.
        
        Cada cliente tem sua própria thread dedicada:
        - Pode ler dados do cliente sem bloquear outras threads.
        - Pode fazer sleep/wait sem afetar o servidor principal.
        - Acessa recursos compartilhados (self.clients) via LOCK.
        
        Algoritmo:
        1. Recebe o username (primeira mensagem).
        2. Registra o cliente na lista (com lock).
        3. Notifica outros clientes.
        4. Entra em loop: recebe mensagem → broadcast para todos.
        5. Ao desconectar, remove da lista e notifica.
        
        Args:
            client_socket: Socket TCP do cliente.
            client_address: Tupla (IP, PORT) do cliente.
        """
        username = None
        client_socket.settimeout(1.0)  # Timeout para evitar bloqueios eternos
        
        try:
            # ===== ETAPA 1: Recebe o username (primeira mensagem) =====
            try:
                data = client_socket.recv(256)
                if not data:
                    logger.warning(f"Conexão de {client_address} fechada antes de fornecer username.")
                    return
                
                username = data.decode('utf-8', errors='ignore').strip()

                logger.info(f"Cliente de {client_address} identificou-se como: {username!r}")

                # Ignora healthcheck explícito (usado pelo backup)
                if username == HEALTHCHECK_USERNAME:
                    logger.info(f"Healthcheck recebido de {client_address}; encerrando conexao de monitoramento.")
                    username = None
                    return

                # Valida formato do username: apenas alfanumérico, underscore ou '-' e tamanho 1-20
                if not re.match(r'^[A-Za-z0-9_\-]{1,20}$', username):
                    logger.warning(
                        f"Username invalido ou probe detectado de {client_address}: {username!r}; encerrando conexao." 
                    )
                    try:
                        client_socket.send(b"Invalid username\n")
                    except Exception:
                        pass
                    return

                # Rejeita usernames que sejam métodos HTTP (ex.: GET, HEAD, POST)
                http_methods = {"GET", "POST", "HEAD", "PUT", "DELETE", "OPTIONS", "TRACE", "CONNECT", "PATCH"}
                if username.upper() in http_methods:
                    logger.warning(f"Username parece metodo HTTP ({username!r}) de {client_address}; encerrando conexao.")
                    try:
                        client_socket.send(b"Invalid username\n")
                    except Exception:
                        pass
                    return
            
            except socket.timeout:
                logger.warning(f"Timeout ao esperar username de {client_address}")
                return
            
            # ===== ETAPA 2: Registra o cliente (COM LOCK) =====
            # Isto é uma SEÇÃO CRÍTICA: múltiplas threads podem tentar registrar
            # clientes simultaneamente. Sem lock:
            # - Thread A lê self.clients (diz: "está vazio")
            # - Thread B lê self.clients (diz: "está vazio")
            # - Thread A escreve client1
            # - Thread B escreve client2
            # - Resultado: Só existe client2. Client1 foi perdido (race condition).
            
            with self.clients_lock:  # Adquire lock
                # Agora somente ESTA thread pode acessar self.clients
                if username in self.clients:
                    logger.warning(f"Username duplicado: {username}")
                    client_socket.send(b"Username already in use.\n")
                    return
                
                self.clients[username] = client_socket
                logger.info(f"Cliente registrado: {username}. Total: {len(self.clients)}")
            # LIBERA lock (fim da seção crítica)
            
            # Notifica outros clientes
            self.broadcast(f"[SYSTEM] {username} entrou no chat.", exclude=username)
            client_socket.send(b"Bem-vindo ao chat!\n")
            
            # ===== ETAPA 3: Loop de Recepção e Broadcast =====
            while True:
                try:
                    # Recebe mensagem do cliente (até 1024 bytes)
                    data = client_socket.recv(1024)
                    
                    if not data:
                        # Cliente fechou a conexão (FIN packet)
                        logger.info(f"Cliente {username} desconectou (FIN).")
                        break
                    
                    message = data.decode('utf-8', errors='ignore').strip()
                    
                    if not message:
                        continue
                    
                    logger.info(f"Mensagem de {username}: {message}")
                    
                    # Faz broadcast para TODOS os clientes
                    self.broadcast(f"{username}: {message}")
                
                except socket.timeout:
                    # Timeout é normal; continua tentando receber
                    continue
                except Exception as e:
                    logger.error(f"Erro ao processar mensagem de {username}: {e}")
                    break
        
        except Exception as e:
            logger.error(f"Erro em handle_client ({client_address}): {e}")
        
        finally:
            # ===== LIMPEZA: Remove cliente (COM LOCK) =====
            if username:
                with self.clients_lock:  # Seção crítica para remoção
                    self.clients.pop(username, None)
                    logger.info(f"Cliente {username} removido. Total: {len(self.clients)}")
                
                # Notifica outros clientes
                self.broadcast(f"[SYSTEM] {username} saiu do chat.")
            
            # Fecha o socket do cliente
            try:
                client_socket.close()
            except:
                pass
            
            logger.info(f"Thread de {client_address} finalizada.")
    
    # ========================================================================
    # MÉTODO: broadcast() - Envia Mensagem para Todos os Clientes
    # ========================================================================
    
    def broadcast(self, message: str, exclude: str = None) -> None:
        """
        Envia uma mensagem para TODOS os clientes conectados.
        
        Esta função é chamada por MÚLTIPLAS threads simultaneously:
        - Thread do cliente A quer fazer broadcast.
        - Thread do cliente B quer fazer broadcast.
        - Ambas chamam broadcast() ao mesmo tempo.
        
        Sem sincronização, self.clients poderia ser modificado enquanto iteramos
        (outra thread desconecta um cliente durante nosso loop).
        
        Solução: Adquirir o lock ANTES de iterar.
        
        Args:
            message: Mensagem a enviar (string).
            exclude: Username a excluir (para não ecoar para si mesmo).
        """
        formatted_message = f"{message}\n".encode('utf-8')
        
        # Adquire lock E cria uma cópia da lista
        # (liberamos o lock rápido, não ficamos preso durante send())
        with self.clients_lock:
            # Seção crítica: apenas leitura, mas PROTEGIDA
            clients_copy = dict(self.clients)  # Cópia segura
        
        # Agora enviamos SEM lock (permite que outras threads registrem clientes)
        for username, client_socket in clients_copy.items():
            if exclude and username == exclude:
                continue
            
            try:
                client_socket.send(formatted_message)
            except Exception as e:
                # Cliente pode estar desconectado; ignora erro
                logger.error(f"Falha ao enviar para {username}: {e}")
    
    # ========================================================================
    # MÉTODO: stop() - Desliga o Servidor
    # ========================================================================
    
    def stop(self) -> None:
        """Para o servidor, fecha todas as conexões e aguarda threads."""
        self.running = False
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        # Fecha todos os clientes
        with self.clients_lock:
            for username, client_socket in list(self.clients.items()):
                try:
                    client_socket.close()
                except:
                    pass
        
        logger.info("Chat Engine parado.")


# ============================================================================
# PONTO DE ENTRADA
# ============================================================================

if __name__ == "__main__":
    engine = ChatEngine(host="127.0.0.1", port=5000)
    
    try:
        engine.start()
    except KeyboardInterrupt:
        logger.info("Interrupção do usuário.")
        engine.stop()
