# 📁 Guia de Estrutura Modular

Bem-vindo! Este documento ajuda você a navegar e explicar o projeto refatorado.

---

## 🎯 3 Componentes Principais

### 1. 🔧 **Chat Engine** (`backend/chat_engine/`)

**O CORAÇÃO do projeto** - Servidor TCP puro com threading manual.

```
chat_engine/
├── __init__.py      → Exports (ChatEngine, HEALTHCHECK_USERNAME)
├── protocol.py      → Validações e constantes
└── server.py        → Classe ChatEngine (a estrela ⭐)
```

**O que explicar:**
- **protocol.py**: Validação de usernames (regex), rejeição de HTTP methods, detecção de probes
- **server.py**: 
  - `start()`: Loop infinito que aceita conexões
  - `handle_client()`: Uma thread por cliente (requisito da disciplina!)
  - `broadcast()`: Envia mensagem com lock thread-safe
  - `clients_lock`: `threading.Lock()` - previne race conditions

**Arquivo de entrada:** `chat_engine.py` (22 linhas)

---

### 2. 🌐 **Web Gateway** (`backend/gateway/`)

**O INTERMEDIÁRIO** - Proxy entre navegador (WebSocket) e engine (TCP).

```
gateway/
├── __init__.py            → Exports (app, socketio, run_app)
├── app.py                 → Flask setup + rotas estáticas + health check
├── socket_handlers.py     → Eventos SocketIO (join, send, disconnect)
├── tcp_proxy.py           → Classe ClientTCPConnection
└── app_context.py         → Context global (evita circular imports)
```

**O que explicar:**
- **app.py**: 
  - Configuração Flask (static_folder, SECRET_KEY)
  - Rota `/` serve index.html
  - Rota `/health` para Render (silenciosa, sem logs)
  - Rota `/demo/kill-engine` para testar failover

- **socket_handlers.py**:
  - `on_join_chat()`: Cliente WebSocket → cria ClientTCPConnection → conecta ao engine
  - `on_send_message()`: Repassa mensagem do navegador para o engine
  - `on_disconnect()`: Fecha conexão TCP quando navegador fecha

- **tcp_proxy.py**:
  - `ClientTCPConnection`: Uma por cliente WebSocket
  - `connect()`: Abre TCP, dispara thread de leitura
  - `_read_from_engine()`: Thread background que lê do engine e emite para navegador
  - `send_to_engine()`: Envia para engine com reconnection automática

**Arquivo de entrada:** `web_gateway.py` (21 linhas)

---

### 3. 🔄 **Backup Server** (`backend/backup/`)

**O MONITOR** - Detecta falha do engine e assume o controle.

```
backup/
├── __init__.py    → Exports (BackupServer)
└── monitor.py     → Classe BackupServer (heartbeat + failover)
```

**O que explicar:**
- `_probe_primary()`: Tenta conectar a cada 2 segundos (heartbeat)
- `monitor_primary()`: Loop que verifica saúde do primário
- `become_primary()`: Quando primário cai, sobe novo ChatEngine na porta 5000

**Arquivo de entrada:** `backup_server.py` (24 linhas)

---

## 📊 Fluxo de Dados

```
┌─────────────────────────────────────────────────────────┐
│         Navegador do Usuário (JavaScript)              │
└─────────────────────────────────────────────────────────┘
                           ↓ WebSocket
┌─────────────────────────────────────────────────────────┐
│    Web Gateway (Flask + SocketIO)                       │
│  ├─ socket_handlers.py: Recebe eventos do navegador    │
│  ├─ tcp_proxy.py: Gerencia conexão TCP com engine      │
│  └─ app.py: Rotas estáticas, health check              │
└─────────────────────────────────────────────────────────┘
                           ↓ TCP
┌─────────────────────────────────────────────────────────┐
│    Chat Engine (Servidor TCP Puro)                     │
│  ├─ server.py: Aceita conexões, spawna threads        │
│  ├─ protocol.py: Valida usernames, detecta probes     │
│  └─ clients_lock: Sincroniza broadcast com lock       │
└─────────────────────────────────────────────────────────┘

Em paralelo (monitorando engine):
┌─────────────────────────────────────────────────────────┐
│    Backup Server (Monitor Ativo-Passivo)              │
│  └─ monitor.py: Heartbeat a cada 2 segundos           │
│     Se engine cair → assume porta 5000                  │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Como Iniciar

```bash
# Validar imports
python test_imports.py

# Iniciar tudo
./start.sh

# Testar failover
curl -X POST http://localhost:10000/demo/kill-engine
```

---

## 📝 Para a Apresentação

### Slide 1: Visão Geral
"O projeto tem 3 componentes: **Chat Engine** (servidor TCP), **Web Gateway** (proxy), e **Backup Server** (failover)."

### Slide 2: Detalhes do Chat Engine
"O chat_engine é o coração. Implementa threading manual:
- Cada cliente é uma thread (`threading.Thread`)
- Todas compartilham `clients` protegido por `threading.Lock`
- Broadcast envia para todos com segurança"

### Slide 3: Detalhes do Gateway
"O gateway é um proxy:
- WebSocket ↔ TCP
- Cada cliente web tem uma `ClientTCPConnection`
- Reconecta automaticamente se o engine falha"

### Slide 4: Failover
"O backup monitora o engine a cada 2 segundos.
Se falhar, sobe um novo engine na mesma porta.
Clientes reconectam automaticamente."

---

## 🔗 Arquivos Importantes

| Arquivo | Linhas | Propósito |
|---------|--------|----------|
| `chat_engine/server.py` | ~150 | Core do threading |
| `chat_engine/protocol.py` | ~80 | Validações |
| `gateway/tcp_proxy.py` | ~200 | Proxy TCP |
| `gateway/socket_handlers.py` | ~140 | Eventos SocketIO |
| `gateway/app.py` | ~150 | Flask setup |
| `backup/monitor.py` | ~130 | Heartbeat |

**Total distribuído!** Nenhum arquivo > 200 linhas.

---

## ✨ Qualidade de Código

- ✅ **PEP8**: 88 caracteres por linha, espaçamento correto
- ✅ **Type hints**: Todos os argumentos/returns tipados
- ✅ **Docstrings**: Explicam o quê, por quê, como
- ✅ **Logging**: Um logger por módulo
- ✅ **Sem circular imports**: app_context.py resolve
- ✅ **SRP**: Uma responsabilidade por classe/módulo

---

## 🎁 Bonus: Testabilidade

Agora é fácil testar:

```python
# Testar protocolo
from chat_engine.protocol import validate_username
assert validate_username("alice")[0] == True
assert validate_username("GET")[0] == False

# Testar engine
from chat_engine import ChatEngine
engine = ChatEngine()
# ... testar start(), handle_client(), broadcast()

# Testar proxy
from gateway.tcp_proxy import ClientTCPConnection
conn = ClientTCPConnection(sid="test", username="alice")
# ... testar connect(), send_to_engine()
```

---

**Tudo pronto para apresentação! 🚀**
