"""
Web Gateway - Proxy/Tradutor entre WebSocket (Navegador) e TCP (Chat Engine).

Este módulo implementa o Padrão Gateway (API Gateway).

Responsabilidades:
1. Servir a interface HTML/JS/CSS na rota raiz `/`.
2. Aceitar conexões WebSocket do navegador (via Flask-SocketIO).
3. Para cada cliente WebSocket, abrir uma conexão TCP como CLIENTE para o chat_engine.
4. Fazer tradução bidirecional de mensagens:
   - Navegador envia via WebSocket → Gateway repassa via TCP
   - Chat Engine envia via TCP → Gateway repassa via WebSocket
5. Gerenciar o ciclo de vida: desconexão de um lado = desconexão do outro.

Por que esse padrão?
- O chat_engine.py é "baixo nível" (threads, sockets, locks) — avaliado pelo professor.
- O web_gateway.py é "alto nível" (Flask, automático) — infraestrutura que facilita.
- Separação de responsabilidades = código limpo e avaliação justa.
"""

import socket
import threading
import logging
import os
import time
from flask import Flask, request, send_from_directory
from flask_socketio import SocketIO, emit, disconnect

# ============================================================================
# CONFIGURAÇÃO DE LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(name)s] - %(message)s'
)
logger = logging.getLogger(__name__)

# Reduz verbosidade do Werkzeug (healthchecks, probes) para não sobrecarregar logs
logging.getLogger('werkzeug').setLevel(logging.WARNING)

# ============================================================================
# CONFIGURAÇÃO FLASK + SOCKETIO
# ============================================================================

app = Flask(__name__, static_folder='../frontend', static_url_path='')
app.config['SECRET_KEY'] = 'seu_secret_key_aqui_mudar_em_producao'

# Força o modo threading no desenvolvimento local.
# Isso evita que o Flask-SocketIO tente usar eventlet automaticamente.
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ============================================================================
# CHAT ENGINE CONNECTION (Gerenciador de Clientes TCP)
# ============================================================================

class ClientTCPConnection:
    """
    Representa a conexão TCP de um cliente específico com o chat_engine.
    
    Esta classe encapsula:
    - A conexão TCP em si (socket).
    - A thread background que lê mensagens do Engine.
    - Métodos para enviar e receber.
    """
    
    def __init__(self, sid: str, username: str, engine_host: str = None, engine_port: int = None):
        """
        Inicializa a conexão TCP.
        
        Args:
            sid: Session ID do SocketIO (identifica o cliente web).
            username: Nome de usuário.
            engine_host: Host do chat_engine.
            engine_port: Porta do chat_engine.
        """
        self.sid = sid
        self.username = username
        self.engine_host = engine_host or os.environ.get("ENGINE_HOST", "127.0.0.1")
        self.engine_port = engine_port or int(os.environ.get("ENGINE_PORT", "5000"))
        self.connect_retries = int(os.environ.get("ENGINE_CONNECT_RETRIES", "5"))
        self.connect_retry_delay = float(os.environ.get("ENGINE_CONNECT_RETRY_DELAY", "1.0"))
        
        self.tcp_socket = None
        self.reader_thread = None
        self.connected = False
    
    def connect(self) -> bool:
        """
        Abre a conexão TCP com o chat_engine e dispara thread de leitura.
        
        Retorna:
            True se conectado com sucesso, False caso contrário.
        """
        try:
            last_error = None

            for attempt in range(1, self.connect_retries + 1):
                try:
                    # Cria socket TCP como CLIENTE
                    self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.tcp_socket.settimeout(5.0)

                    # Conecta ao chat_engine
                    self.tcp_socket.connect((self.engine_host, self.engine_port))
                    logger.info(f"[{self.sid}] Conectado ao chat_engine ({self.engine_host}:{self.engine_port})")

                    # Envia username como primeira mensagem com NEWLINE para separar do próximo
                    self.tcp_socket.send((self.username + '\n').encode('utf-8'))

                    self.connected = True

                    # ===== DISPARA THREAD DE LEITURA EM BACKGROUND =====
                    # Esta thread ficará esperando mensagens do chat_engine
                    # e as repassará para o navegador via WebSocket (emit).
                    self.reader_thread = threading.Thread(
                        target=self._read_from_engine,
                        daemon=True,
                        name=f"TCPReader-{self.sid}"
                    )
                    self.reader_thread.start()
                    logger.info(f"[{self.sid}] Thread de leitura iniciada ({self.reader_thread.name})")

                    return True

                except Exception as error:
                    last_error = error
                    logger.warning(
                        f"[{self.sid}] Tentativa {attempt}/{self.connect_retries} falhou ao conectar ao chat_engine: {error}"
                    )
                    self.disconnect()

                    if attempt < self.connect_retries:
                        time.sleep(self.connect_retry_delay)

            logger.error(f"[{self.sid}] Nao foi possivel conectar ao chat_engine apos {self.connect_retries} tentativas: {last_error}")
            return False
        
        except Exception as e:
            logger.error(f"[{self.sid}] Erro ao conectar ao chat_engine: {e}")
            self.disconnect()
            return False
    
    def _read_from_engine(self) -> None:
        """
        Thread background: lê mensagens do chat_engine e repassa ao navegador.
        
        Esta função executa em uma thread separada:
        - Bloqueia em tcp_socket.recv() esperando dados do Engine.
        - Quando recebe dados, emite via WebSocket para o navegador.
        - Continua até a desconexão.
        
        Tratamento de erros:
        - Se o Engine desconecta, encerra a thread.
        - Erros de rede são capturados e logados.
        """
        try:
            while self.connected:
                try:
                    # Bloqueia esperando dados do chat_engine
                    data = self.tcp_socket.recv(1024)
                    
                    if not data:
                        # Chat_engine fechou a conexão (FIN)
                        logger.info(f"[{self.sid}] Chat Engine desconectou")
                        break
                    
                    message = data.decode('utf-8', errors='ignore').strip()
                    
                    if message:
                        logger.info(f"[{self.sid}] Recebido do Engine: {message}")
                        # Ignora mensagens que parecem ser probes HTTP (ex.: HEAD/GET requests)
                        if 'HTTP/' in message or message.startswith('HEAD ') or message.startswith('GET '):
                            logger.info(f"[{self.sid}] Ignorando mensagem de probe HTTP vinda do Engine: {message.splitlines()[0]!r}")
                            continue

                        # ===== EMITE PARA O NAVEGADOR VIA WEBSOCKET =====
                        # socketio.emit envia a mensagem para o cliente específico
                        socketio.emit('receive_message', {'message': message}, room=self.sid)
                
                except socket.timeout:
                    # Timeout é normal; continua tentando
                    continue
                except Exception as e:
                    logger.error(f"[{self.sid}] Erro ao ler do Engine: {e}")
                    break
        
        finally:
            self.disconnect()
    
    def send_to_engine(self, message: str) -> bool:
        """
        Envia uma mensagem para o chat_engine via TCP.
        
        Args:
            message: Mensagem a enviar.
        
        Retorna:
            True se enviado com sucesso, False caso contrário.
        """
        if not self.connected or not self.tcp_socket:
            logger.warning(f"[{self.sid}] Socket desconectado; tentando reconectar antes de enviar")
            if not self.connect():
                return False
        
        try:
            self.tcp_socket.send((message + '\n').encode('utf-8'))
            logger.info(f"[{self.sid}] Enviado para Engine: {message}")
            return True
        except Exception as e:
            logger.error(f"[{self.sid}] Erro ao enviar para Engine: {e}")
            self.disconnect()
            if self.connect():
                try:
                    self.tcp_socket.send((message + '\n').encode('utf-8'))
                    logger.info(f"[{self.sid}] Enviado para Engine apos reconexao: {message}")
                    return True
                except Exception as retry_error:
                    logger.error(f"[{self.sid}] Falha ao reenviar apos reconexao: {retry_error}")
                    self.disconnect()
            return False
    
    def disconnect(self) -> None:
        """
        Fecha a conexão TCP e libera recursos.
        """
        self.connected = False
        
        if self.tcp_socket:
            try:
                self.tcp_socket.close()
            except:
                pass
        
        logger.info(f"[{self.sid}] Desconectado do chat_engine")


# ============================================================================
# MAPEAMENTO GLOBAL: SID -> ClientTCPConnection
# ============================================================================

# Esta estrutura mapeia cada sessão WebSocket (identificada por sid)
# para sua conexão TCP correspondente com o chat_engine.
clients_map = {}
clients_map_lock = threading.Lock()


def get_client_connection(sid: str) -> ClientTCPConnection:
    """Obtém a conexão TCP de um cliente pelo SID."""
    with clients_map_lock:
        return clients_map.get(sid)


def register_client_connection(sid: str, connection: ClientTCPConnection) -> None:
    """Registra uma nova conexão TCP."""
    with clients_map_lock:
        clients_map[sid] = connection


def unregister_client_connection(sid: str) -> None:
    """Remove uma conexão TCP."""
    with clients_map_lock:
        if sid in clients_map:
            del clients_map[sid]


# ============================================================================
# ROTAS FLASK - Serviço de Arquivos Estáticos
# ============================================================================

@app.route('/')
def index():
    """Serve o index.html (interface do chat)."""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/health')
def health_check():
    """
    Health check endpoint para Render (e qualquer load balancer).
    
    Render faz requisições periódicas a este endpoint para confirmar
    que o serviço está vivo. Retorna 200 OK imediatamente.
    
    Não é logado (silencioso) para não poluir os logs.
    """
    return 'OK', 200


@app.route('/<path:filename>')
def serve_static(filename):
    """Serve arquivos estáticos (CSS, JS, etc)."""
    return send_from_directory(app.static_folder, filename)


# ============================================================================
# ENDPOINT DEMO - Para testar failover
# ============================================================================

@app.route('/demo/kill-engine', methods=['POST'])
def demo_kill_engine():
    """
    [DEMO ONLY] Simula falha do engine matando as conexões TCP.
    
    Isso permite testar o failover do backup server SEM matar todo o serviço.
    Apenas o engine é "morto", o backup detecta e assume.
    
    Uso:
    - Localmente: curl -X POST http://localhost:10000/demo/kill-engine
    - Render: curl -X POST https://chat-distribuido-m46j.onrender.com/demo/kill-engine
    """
    logger.warning("=" * 60)
    logger.warning("[DEMO] SIMULATING ENGINE FAILURE - Killing all TCP connections")
    logger.warning("=" * 60)
    
    # Desconecta todos os clientes do engine
    dead_count = 0
    for sid, connection in list(clients_map.items()):
        try:
            logger.info(f"[DEMO] Closing TCP connection for {sid}")
            connection.disconnect()
            dead_count += 1
        except Exception as e:
            logger.error(f"[DEMO] Error closing {sid}: {e}")
    
    logger.warning(f"[DEMO] Killed {dead_count} connections. Backup should take over in ~2 seconds.")
    logger.warning("=" * 60)
    
    return {
        "status": "ok",
        "message": f"Simulated engine failure. Killed {dead_count} TCP connections. Backup should assume control in ~2 seconds."
    }, 200


# ============================================================================
# EVENTOS SOCKETIO
# ============================================================================

@socketio.on('join_chat')
def on_join_chat(data):
    """
    Chamado quando um usuário tenta se conectar ao chat.
    
    Fluxo:
    1. Recebe username do navegador.
    2. Cria uma ClientTCPConnection (abre socket TCP para chat_engine).
    3. Se bem-sucedido, notifica o cliente.
    4. Se falhar, retorna erro.
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
            emit('connection_error', {'error': 'Falha ao conectar ao chat engine'})
            return
        
        # Registra no mapa global
        register_client_connection(sid, tcp_connection)
        
        logger.info(f"[{sid}] Conectado com sucesso ao chat engine")
        emit('connection_success', {'username': username})
    
    except Exception as e:
        logger.error(f"[{sid}] Erro ao processar join_chat: {e}")
        emit('connection_error', {'error': str(e)})


@socketio.on('send_message')
def on_send_message(data):
    """
    Chamado quando o usuário envia uma mensagem via WebSocket.
    
    Fluxo:
    1. Recupera a conexão TCP do mapa.
    2. Envia a mensagem para o chat_engine via TCP.
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


@socketio.on('disconnect')
def on_disconnect():
    """
    Chamado quando o cliente desconecta (fecha navegador, perde conexão, etc).
    
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


# ============================================================================
# PONTO DE ENTRADA
# ============================================================================

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Web Gateway iniciando...")
    logger.info("=" * 60)
    logger.info("Certifique-se de que o chat_engine.py está rodando em localhost:5000")
    
    # Para desenvolvimento local, usa port 5001.
    # Para deploy no Render.com, usa variável de ambiente PORT.
    port = int(os.environ.get('PORT', 5001))
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    
    logger.info(f"Abra http://localhost:{port} no navegador")
    logger.info("=" * 60)
    
    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        debug=debug_mode,
        use_reloader=False,
        allow_unsafe_werkzeug=True
    )
