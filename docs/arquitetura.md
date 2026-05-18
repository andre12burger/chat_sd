# Arquitetura Técnica - Chat Multiusuário

## 1. Visão Geral da Arquitetura

```
┌──────────────────────────────┐
│   Navegador (Usuário)        │
│  HTML/JS/CSS (Interface)     │
└──────────────┬───────────────┘
               │
        WebSocket (Port 5001)
               │
┌──────────────▼───────────────┐
│  web_gateway.py              │
│  (Flask + Flask-SocketIO)    │
│  ✓ Serve interface HTML      │
│  ✓ Proxy WebSocket <-> TCP   │
│  ✓ Gerencia threads reader   │
└──────────────┬───────────────┘
               │
        TCP Puro (localhost:5000)
               │
┌──────────────▼───────────────┐
│  chat_engine.py              │
│  (Socket + Threading Puro)   │
│  ✓ Motor central             │
│  ✓ Threads por cliente       │
│  ✓ Locks para sincronização  │
│  ✓ Broadcast thread-safe     │
└──────────────────────────────┘
```

## 2. Camada 1: Chat Engine (O Coração)

### Arquivo: `backend/chat_engine.py`

**Responsabilidades:**
- Aceitar conexões TCP (socket.accept)
- Instanciar 1 threading.Thread por cliente
- Sincronizar com threading.Lock
- Fazer broadcast thread-safe

**Estrutura de Dados Crítica:**

```python
self.clients: Dict[str, socket.socket] = {}  # username -> socket do cliente
self.clients_lock = threading.Lock()          # Protege acesso simultâneo
```

**Por que o Lock é necessário:**

Sem lock, duas threads podem corromper o dicionário:

```
Timeline SEM Lock:
T1: Lê self.clients (vazio)
T2: Lê self.clients (vazio)
T1: Escreve client_a
T2: Escreve client_b
Resultado: Apenas client_b existe! (race condition)

Timeline COM Lock:
T1: Adquire lock
T1: Lê self.clients (vazio)
T1: Escreve client_a
T1: Libera lock
T2: Adquire lock
T2: Lê self.clients (tem client_a)
T2: Escreve client_b
T2: Libera lock
Resultado: Ambos existem ✓
```

**Seções Críticas Protegidas:**

1. **Registrar cliente:**
```python
with self.clients_lock:  # COMEÇA SEÇÃO CRÍTICA
    if username in self.clients:
        return False  # Erro: duplicado
    self.clients[username] = socket
    # TERMINA SEÇÃO CRÍTICA
```

2. **Fazer broadcast:**
```python
with self.clients_lock:
    clients_copy = dict(self.clients)  # Cópia segura

# Agora envia SEM lock (não bloqueia registro de novos clientes)
for client_socket in clients_copy.values():
    client_socket.send(message)
```

3. **Remover cliente:**
```python
with self.clients_lock:
    self.clients.pop(username, None)
```

**Fluxo por Cliente (Cada thread executa isso):**

```
handle_client(client_socket, client_address):
  1. Recebe username (primeira mensagem)
  2. Valida e registra (com lock)
  3. Loop infinito:
     a. Recebe mensagem do cliente
     b. Faz broadcast para todos (com lock)
     c. Se cliente desconecta, break
  4. Finally: Remove cliente (com lock)
```

---

## 3. Camada 2: Web Gateway (O Tradutor)

### Arquivo: `backend/web_gateway.py`

**Responsabilidades:**
- Servir HTML/CSS/JS (interface)
- Aceitar WebSocket do navegador (Flask-SocketIO)
- Abrir TCP como cliente para chat_engine
- Traduzir bidirecionalmente

**Padrão: Gateway (Proxy)**

```
Navegador                Gateway             Chat Engine
  │                         │                    │
  ├─ WebSocket Connect ───→ │                    │
  │                         ├─ TCP Connect ────→ │
  │                         │ ← Success          │
  │ ← Connection OK ────────┤                    │
  │                         │                    │
  ├─ Send "Olá" ─────────→  │                    │
  │                         ├─ Send "Olá" ──→   │
  │                         │                    │
  │                         │ ← Broadcast "A: Olá"
  │ ← "A: Olá" ────────────  │                    │
  │                         │ ← Broadcast "B: Oi"
  │ ← "B: Oi" ────────────   │                    │
  │                         │                    │
```

**Classe: ClientTCPConnection**

Para cada cliente WebSocket, existe UM ClientTCPConnection:
- `self.tcp_socket`: Socket TCP como cliente
- `self.reader_thread`: Thread background que lê do engine
- `self.connected`: Flag de status

**Mapa Global:**

```python
clients_map: Dict[str, ClientTCPConnection] = {}
# Mapeia: session_id (SocketIO) → ClientTCPConnection
```

**Fluxo: Usuário Envia Mensagem**

```
1. Navegador emite via WebSocket: 'send_message'
2. Flask-SocketIO chama: on_send_message()
3. Recupera ClientTCPConnection do clients_map
4. Envia via TCP: client_tcp_connection.send_to_engine(message)
5. Thread reader do socket TCP recebe no chat_engine
6. Chat_engine faz broadcast
7. Broadcast volta para gateway (thread reader captura)
8. Gateway emite para todos os clientes: 'receive_message'
```

**Thread Reader (Background):**

```python
def _read_from_engine():
    while self.connected:
        data = self.tcp_socket.recv(1024)  # Bloqueia esperando dados
        if not data:  # Engine fechou conexão
            break
        message = data.decode('utf-8')
        # Emite para navegador:
        socketio.emit('receive_message', {'message': message}, room=self.sid)
```

---

## 4. Protocolo de Comunicação

### TCP (Entre Gateway e Engine)

**Formato:** Texto UTF-8, terminado com newline

```
[CLIENT 1]
├─ Envia: "alice"                    # Handshake: username
├─ Recebe: "Bem-vindo ao chat!"
├─ Envia: "Olá pessoal"
└─ Recebe: "alice: Olá pessoal"

[ENGINE - Broadcast]
├─ Recebe de alice: "Olá pessoal"
├─ Envia para bob:  "alice: Olá pessoal"
└─ Envia para charlie: "alice: Olá pessoal"
```

### WebSocket (Entre Navegador e Gateway)

**Eventos:**

```javascript
// Cliente → Gateway
socket.emit('join_chat', { username: 'alice' })
socket.emit('send_message', { message: 'Olá!' })

// Gateway → Cliente
socket.on('connection_success', data => { ... })
socket.on('receive_message', data => { ... })
socket.on('connection_error', data => { ... })
```

---

## 5. Sincronização e Thread-Safety

### Lock Hierarchy

```
clients_lock (em chat_engine.py)
  └─ Protege: self.clients (Dict[str, socket])

clients_map_lock (em web_gateway.py)
  └─ Protege: clients_map (Dict[str, ClientTCPConnection])
```

### Deadlock Prevention

- Locks são adquiridos por tempo curto (escopo `with`)
- Nunca duas threads tentam adquirir dois locks (evita deadlock)
- Broadcast copia a lista DENTRO do lock, mas envia FORA

---

## 6. Fluxo Completo: Dois Usuários Conversando

```
┌─ INICIALIZAÇÃO ─────────────────────────────────────────┐

T=0s:  Alice abre browser, conecta
       ↓ WebSocket to Gateway
       Gateway abre TCP para Engine
       ↓ TCP
       Engine thread alice_handler criada

T=1s:  Bob abre browser, conecta
       ↓ WebSocket to Gateway
       Gateway abre TCP para Engine
       ↓ TCP
       Engine thread bob_handler criada

Resultado:
┌─ chat_engine.py ─┐  ┌─ web_gateway.py ─┐  ┌─ Navegadores ─┐
│ alice_thread      │  │ alice_connection  │  │ Alice (WS)     │
│ bob_thread        │  │ bob_connection    │  │ Bob (WS)       │
└──────────────────┘  └───────────────────┘  └────────────────┘

└─────────────────────────────────────────────────────────┘

┌─ COMUNICAÇÃO ───────────────────────────────────────────┐

T=2s: Alice digita "Olá Bob!" e clica Enviar
      
      Navegador (Alice)
      ↓ emit('send_message', {message: 'Olá Bob!'})
      
      Gateway (on_send_message)
      ├─ Recupera tcp_connection de alice
      ├─ Envia via TCP: "Olá Bob!"
      
      Engine (alice_thread)
      ├─ recv: "Olá Bob!"
      ├─ broadcast: "alice: Olá Bob!"
      │  ├─ Envia para alice_socket
      │  └─ Envia para bob_socket
      
      Gateway (reader_thread de alice)
      ├─ recv: "alice: Olá Bob!"
      ├─ emit para alice: {message: 'alice: Olá Bob!'}
      
      Gateway (reader_thread de bob)
      ├─ recv: "alice: Olá Bob!"
      ├─ emit para bob: {message: 'alice: Olá Bob!'}
      
      Navegadores
      ├─ Alice vê: "alice: Olá Bob!"
      └─ Bob vê: "alice: Olá Bob!"

└─────────────────────────────────────────────────────────┘
```

---

## 7. Tratamento de Falhas

### Desconexão do Cliente

```
Bob fecha o browser:
  1. Gateway detecta disconnect via WebSocket
  2. Chama on_disconnect()
  3. Fecha tcp_connection de bob
  4. Remove bob do clients_map
  5. Engine reader_thread detecta FIN
  6. handle_client finaliza, remove bob da lista
  7. Broadcast notifica alice: "[SYSTEM] bob saiu do chat"
```

### Reconexão Automática

Gateway usa Flask-SocketIO com suporte a reconexão automática:
```javascript
const socket = io({
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000,
    reconnectionAttempts: 5
});
```

---

## 8. Melhorias Futuras

1. **Persistence**: Adicionar backup_server.py (replicação ativa-passiva)
2. **Criptografia**: TLS para TCP, HTTPS para Web
3. **Autenticação**: Usuário/senha, tokens JWT
4. **Salas**: Suporte a múltiplos rooms de chat
5. **Histórico**: Armazenar mensagens em BD
6. **Rate Limiting**: Evitar spam

---

## 9. Testando Localmente

### Terminal 1: Engine
```bash
python backend/chat_engine.py
```

### Terminal 2: Gateway
```bash
python backend/web_gateway.py
```

### Navegadores
```
http://localhost:5001
http://localhost:5001  (abra 2+ abas para simular múltiplos clientes)
```

### Verificação de Threads
No `chat_engine.py`, procure por log:
```
ClientThread-54321 iniciada. Total de threads ativas: 3
```

Isso prova que você instanciou threads manualmente ✓

---

**Documento gerado para relatório acadêmico em Overleaf.**
