# 🧪 Guia Completo de Testes - Chat Distribuído

Documentação exhaustiva de como testar o sistema localmente e em produção, com todos os comandos de demonstração e explicação de cada funcionalidade.

**Versão:** 2026-05-18  
**URL de Produção:** https://chat-distribuido-m46j.onrender.com

---

## Índice

1. [Funcionalidades de Usuário](#funcionalidades-de-usuário-e-implementação)
2. [Testes Locais (Desenvolvimento)](#testes-locais-desenvolvimento)
3. [Testes em Produção (Render)](#testes-em-produção-render)
4. [Testes de Resiliência e Failover](#testes-de-resiliência-e-failover)
5. [Testes de Segurança](#testes-de-segurança)
6. [Troubleshooting](#troubleshooting)
7. [FAQ](#faq)

---

## Funcionalidades de Usuário e Implementação

### 1️⃣ Login e Conexão

**O que o usuário vê:**
- Campo para inserir username
- Botão "Conectar"
- Mensagem "Conectando..." enquanto estabelece conexão
- Confirmação "Bem-vindo ao chat, [username]!" ao conectar

**Como foi implementado:**
- **Frontend:** `frontend/client_app.js` → função `connectToChat()`
  - Captura username do input HTML
  - Emite evento Socket.IO `join_chat` com o username
- **Gateway:** `backend/gateway/socket_handlers.py` → handler `on_join_chat`
  - Recebe o `join_chat` do cliente
  - Cria `ClientTCPConnection` (nova instância do proxy)
  - Conecta ao chat engine TCP na porta 5000
  - Envia o username para o engine
- **Engine:** `backend/chat_engine/server.py`
  - Valida o username (regex: alfanuméricos, 1-20 chars)
  - Se válido: envia "Bem-vindo ao chat, [username]!" e registra o cliente
  - Se inválido: rejeitado (conexão fechada)
- **Reconexão:** `backend/gateway/tcp_proxy.py`
  - Se TCP cair após login bem-sucedido, a `ClientTCPConnection` reconecta automaticamente
  - Reenuncia `system_state` globalmente para atualizar dashboards de todos os usuários

**Teste prático:**
```bash
# Abra 2 abas em http://localhost:5001
# Aba 1: Username "alice" → vê "Bem-vindo ao chat, alice!"
# Aba 2: Username "bob" → vê "Bem-vindo ao chat, bob!"
# Ambos aparecem na lista "Usuários Conectados"
```

---

### 2️⃣ Troca de Mensagens (Chat)

**O que o usuário vê:**
- Caixa de input para digitar mensagem
- Botão "Enviar" ou Enter para enviar
- Mensagens aparecem em tempo real em todos os clientes conectados
- Formato: `[nome]: mensagem`

**Como foi implementado:**
- **Frontend:** `frontend/client_app.js`
  - Evento `send_message`: envia `{ message: "..." }` via Socket.IO
  - Evento `receive_message`: renderiza mensagens recebidas em HTML
- **Gateway:** `backend/gateway/socket_handlers.py`
  - Handler `on_send_message`: recebe mensagem do usuário
  - Envia para o engine TCP: `[username]: mensagem\n`
  - Engine retorna a mesma mensagem (confirmação)
  - Gateway emite `receive_message` para TODOS os clientes conectados
- **Engine:** `backend/chat_engine/server.py`
  - Recebe a mensagem do proxy
  - Broadcast thread-safe (com `threading.Lock`) para todos os clientes TCP conectados
  - Cada cliente vê a mensagem (inclusive quem enviou)

**Teste prático:**
```bash
# Terminal com 3 abas abertas, cada uma com um username diferente
# Aba A (alice): digita "Olá, mundo!"
# Abas B e C veem: "[alice]: Olá, mundo!" em tempo real
# Aba B (bob): responde "Oi alice!"
# Todas veem: "[bob]: Oi alice!"
```

---

### 3️⃣ Dashboard de Telemetria (System State)

**O que o usuário vê:**
- Painel à direita mostrando:
  - `SERVIDOR: Primary` ou `SERVIDOR: Backup`
  - `THREAD ID DO CLIENTE: xxx` (identificador único do thread)
  - `CONECTADOS: n usuários`
  - `ÚLTIMO FAILOVER: data/hora ou Nenhum`
  - `MOTIVO: razão do failover ou Nenhum`

**Como foi implementado:**
- **Backend (coleta de dados):**
  - `backend/runtime_status.py`: lê/escreve `backend/.runtime/system_status.json`
    - Campo: `server_role` ("primary" ou "backup")
    - Campo: `connected_users` (array de usernames)
    - Campo: `last_failover_at` (ISO timestamp)
    - Campo: `last_failover_reason` (string descritiva)
  - `backend/gateway/app.py` → `_build_system_state_snapshot()`
    - Coleta dados do arquivo de status
    - Coleta número de clientes conectados do `clients_map`
    - Constrói o objeto `system_state` com todos os dados

- **Backend (emissão):**
  - `backend/gateway/app.py` → `_system_monitor_loop()`
    - Thread que emite `system_state` para **todos os clientes** a cada 2 segundos
  - `backend/gateway/tcp_proxy.py`
    - Quando TCP reconecta após falha, emite `system_state` imediatamente
    - Garante que frontends saibam que reconectou

- **Frontend (renderização):**
  - `frontend/client_app.js` → `updateSystemDashboard(state)`
    - Recebe o evento `system_state`
    - Atualiza HTML com `server_role`, `connected_users`, timestamps
    - CSS (`frontend/style.css`) pode ocultar o painel para modo apresentação

**Teste prático:**
```bash
# Abra http://localhost:5001 em 2 abas, conecte como alice e bob
# Veja no dashboard de ambas:
# ✓ SERVIDOR: Primary
# ✓ CONECTADOS: 2 usuários
# ✓ Ambas veem alice e bob na lista

# Agora execute: curl -X POST http://localhost:5001/demo/kill-engine
# Espere 2-3 segundos
# Veja dashboard mudar para:
# ✓ SERVIDOR: Backup
# ✓ ÚLTIMO FAILOVER: [timestamp do evento]
# ✓ MOTIVO: Heartbeat do primário falhou
```

---

### 4️⃣ Banner de Failover (Server Change)

**O que o usuário vê:**
- Quando o servidor muda de Primary → Backup:
  - Banner destacado: `⚠️ SERVIDOR MUDOU PARA BACKUP`
  - Duração: 5 segundos, depois desaparece
  - Cor: amarelo/orange para chamar atenção

**Como foi implementado:**
- **Backend (detecção de mudança):**
  - `backend/backup/monitor.py` → quando o backup assume:
    - Escreve `system_status.json` com `server_role: "backup"` e `last_failover_reason`
    - O monitor do gateway detecta a mudança comparando snapshots
  
- **Backend (emissão de evento):**
  - `backend/gateway/app.py` → `_system_monitor_loop()`
    - Compara `server_role` anterior com atual
    - Se mudou, emite evento `server_change` com `{ server_role, server_label, message }`
    - Emite para **TODOS os clientes globalmente** (broadcast)

- **Frontend (renderização):**
  - `frontend/client_app.js` → `showFailoverBanner(message)`
    - Recebe evento `server_change`
    - Cria elemento HTML com banner destacado
    - Define timeout de 5 segundos para remover
    - Usa CSS com `display: block` para mostrar

**Por que não mostra sempre:**
- Banner só aparece em eventos reais (não persiste)
- É emitido **apenas uma vez** quando a mudança é detectada
- Protege contra falsos positivos (login não dispara banner)

**Teste prático:**
```bash
# Conecte 1-2 usuários em http://localhost:5001
# Terminal: curl -X POST http://localhost:5001/demo/kill-engine
# Navegador: Banner aparece por 5 segundos: "⚠️ SERVIDOR MUDOU PARA BACKUP"
# Depois desaparece automaticamente
```

---

### 5️⃣ Lista de Usuários Conectados

**O que o usuário vê:**
- Painel (ou seção) mostrando:
  - `USUÁRIOS CONECTADOS: n`
  - Lista de nomes: alice, bob, charlie, ...
  - Atualiza em tempo real conforme usuários entram/saem

**Como foi implementado:**
- **Backend (coleta):**
  - `backend/chat_engine/server.py`
    - Mantém `connected_clients` (lista de `ClientThread`)
    - Cada thread registra seu username ao conectar
    - Remove username ao desconectar
  - `backend/gateway/socket_handlers.py`
    - Handler `on_disconnect`: remove cliente do `clients_map`
    - Emite `system_state` com lista atualizada

- **Backend (emissão):**
  - `backend/gateway/app.py` → `_build_system_state_snapshot()`
    - Lê lista de clientes do `clients_map`
    - Extrai usernames
    - Inclui no objeto `system_state`

- **Frontend (renderização):**
  - `frontend/client_app.js` → `renderConnectedUsers(users)`
    - Recebe lista do evento `system_state`
    - Renderiza HTML com nomes
    - Atualiza a cada novo `system_state`

**Teste prático:**
```bash
# Abra 3 abas, conecte alice, bob, charlie
# Dashboard mostra: "USUÁRIOS CONECTADOS: 3" e lista todos os nomes
# Feche uma aba (charlie desconecta)
# Dashboard atualiza para "USUÁRIOS CONECTADOS: 2"
```

---

### 6️⃣ Identificação do Thread ID (System Info)

**O que o usuário vê:**
- No dashboard: `THREAD ID DO CLIENTE: ...`
- Identificador único (UUID) para cada conexão

**Como foi implementado:**
- **Backend (geração):**
  - `backend/gateway/socket_handlers.py` → `on_join_chat`
    - Cria nova `ClientTCPConnection` com `self.sid` (Socket.IO session ID)
    - Este `sid` é o identificador único por aba/navegador

- **Backend (transmissão):**
  - `backend/gateway/tcp_proxy.py`
    - Ao conectar ao engine, envia mensagens `__SYSTEM_INFO__ {...}`
    - Inclui o `sid` no JSON
  - O engine retorna a informação (ou gateway injeta)

- **Frontend (renderização):**
  - `frontend/client_app.js` → `updateSystemDashboard(state)`
    - Recebe campo `client_thread_id` ou similar
    - Exibe no dashboard

**Significado:**
- Cada aba = 1 Socket.IO connection = 1 `sid` único
- Mesmo usuário em 2 abas = 2 `sid`s diferentes
- Importante para debugging: "qual aba causou isso?"

**Teste prático:**
```bash
# Abra 2 abas
# Aba 1: Vê "THREAD ID: aaaa-bbbb-cccc-dddd"
# Aba 2: Vê "THREAD ID: xxxx-yyyy-zzzz-wwww" (diferente!)
# Ambas veem um "thread" diferente = conexões independentes
```

---

## Testes Locais (Desenvolvimento)

### Setup Inicial

```bash
# 1. Clone e entre no diretório
cd Chat_SD

# 2. Crie virtualenv
python -m venv .venv

# 3. Ative
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1

# Linux/Mac:
source .venv/bin/activate

# 4. Instale dependências
pip install -r requirements.txt

# 5. (Opcional) Resetar estado antes de teste limpo
# Windows:
.\reset_state.ps1
# Linux/Mac:
./reset_state.sh
```

### Teste 1: Conexão Básica (Chat Simples)

**Objetivo:** Verificar que 2+ usuários conseguem trocar mensagens

**Passos:**

1. **Terminal 1** (Chat Engine):
```bash
python backend/chat_engine.py
```
Esperado:
```
2026-05-18 10:00:00,123 - [MainThread] - Chat Engine iniciado em 0.0.0.0:5000
```

2. **Terminal 2** (Backup Server):
```bash
python backend/backup_server.py
```
Esperado:
```
2026-05-18 10:00:02,456 - [MainThread] - Backup server monitorando...
```

3. **Terminal 3** (Web Gateway):
```bash
python backend/web_gateway.py
```
Esperado:
```
 * Running on http://0.0.0.0:5001
```

4. **Navegador:**
- Aba 1: http://localhost:5001 → Username "alice" → Conectar
- Aba 2: http://localhost:5001 → Username "bob" → Conectar

5. **Teste Chat:**
- Aba 1 (alice): Digite "Oi Bob!"
- Aba 2 (bob): Verifica se vê `[alice]: Oi Bob!`
- Aba 2 (bob): Digite "E aí Alice!"
- Aba 1 (alice): Verifica se vê `[bob]: E aí Alice!`

**Checklist:**
- ✅ Ambas conectam sem erro
- ✅ Mensagens aparecem em tempo real
- ✅ Dashboard mostra 2 usuários conectados
- ✅ Logs mostram threads criadas (`ClientThread-...`)

---

### Teste 2: Failover com Backup (Tolerância a Falhas)

**Objetivo:** Verificar que quando o server principal cai, o backup assume

**Passos:**

1. Siga a config do Teste 1 (3 terminais rodando, 2 abas conectadas)

2. **Terminal 4** (Execução do comando demo):
```bash
# Windows (PowerShell):
Invoke-WebRequest -Uri "http://localhost:5001/demo/kill-engine" -Method POST

# Linux/Mac (curl):
curl -X POST http://localhost:5001/demo/kill-engine
```

3. **Observar:**
- Terminal 1 (engine): Pode mostrar erro (conexão fechada)
- Terminal 2 (backup): Deve mostrar:
  ```
  Servidor principal indisponível. Assumindo controle...
  Chat Engine iniciado em 127.0.0.1:5000
  ```
- Terminal 3 (gateway): Mostra reconexão:
  ```
  [gateway.tcp_proxy] Socket desconectado; tentando reconectar
  [gateway.tcp_proxy] Conectado ao chat_engine
  ```
- Navegador (abas):
  - Breve congelamento (1-3 segundos)
  - Banner aparece: `⚠️ SERVIDOR MUDOU PARA BACKUP`
  - Dashboard muda para `SERVIDOR: Backup`
  - Ambas as abas continuam funcionando
  - Conseguem enviar/receber mensagens normalmente

4. **Teste contínuo:**
- Alice e bob continuam trocando mensagens durante/após o failover
- Nenhuma mensagem é perdida
- Nenhum reconexão manual necessária

**Checklist:**
- ✅ Failover dispara em ~2-3 segundos
- ✅ Usuários reconectam automaticamente
- ✅ Chat continua funcionando
- ✅ Dashboard atualiza para "Backup"
- ✅ Banner de failover aparece
- ✅ Nenhuma perda de dados

---

### Teste 3: Validação de Username

**Objetivo:** Garantir que usernames inválidos são rejeitados

**Passos:**

1. Abra terminal Python:
```bash
python
```

2. Execute:
```python
import socket

def test_username(username, expected_valid=True):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('127.0.0.1', 5000))
        s.sendall(f"{username}\n".encode())
        response = s.recv(1024).decode()
        s.close()
        is_valid = "Bem-vindo" in response or "Invalid" not in response
        status = "✅" if is_valid == expected_valid else "❌"
        print(f"{status} '{username}': {response.strip()[:50]}")
        return is_valid == expected_valid
    except Exception as e:
        print(f"❌ '{username}': Erro de conexão")
        return False

# Testes
print("=== USERNAME VÁLIDOS ===")
test_username("alice", expected_valid=True)
test_username("bob123", expected_valid=True)
test_username("user_name", expected_valid=True)

print("\n=== USERNAME INVÁLIDOS ===")
test_username("alice@bob", expected_valid=False)  # Contém @
test_username("alice bob", expected_valid=False)  # Contém espaço
test_username("a" * 25, expected_valid=False)     # Muito longo
test_username("", expected_valid=False)           # Vazio
```

**Esperado:**
```
=== USERNAME VÁLIDOS ===
✅ 'alice': Bem-vindo ao chat, alice!
✅ 'bob123': Bem-vindo ao chat, bob123!
✅ 'user_name': Bem-vindo ao chat, user_name!

=== USERNAME INVÁLIDOS ===
❌ 'alice@bob': Invalid username
❌ 'alice bob': Invalid username
❌ 'aaaa...': Invalid username
❌ '': Invalid username
```

**Checklist:**
- ✅ Todos os testes válidos passam
- ✅ Todos os testes inválidos falham

---

### Teste 4: Resetar Histórico de Failover

**Objetivo:** Verificar que o reset retorna sistema ao estado inicial

**Passos:**

1. Com sistema rodando (3 terminais), execute um failover:
```bash
curl -X POST http://localhost:5001/demo/kill-engine
# Wait 3 seconds
```

2. Verifique dashboard: deve mostrar
   - `SERVIDOR: Backup`
   - `ÚLTIMO FAILOVER: 2026-05-18T...`
   - `MOTIVO: Heartbeat...`

3. Resetar failover:
```bash
curl -X POST http://localhost:5001/demo/reset-failover-history
```

4. Verifique dashboard: deve voltar a
   - `SERVIDOR: Backup` ← (role não muda, só o histórico)
   - `ÚLTIMO FAILOVER: Nenhum`
   - `MOTIVO: Nenhum`

5. Conectar novo usuário:
   - Aba 3: username "charlie" → Conectar
   - Vê dashboard com failover limpo
   - Consegue trocar mensagens com alice e bob

**Checklist:**
- ✅ Reset endpoint funciona (HTTP 200)
- ✅ Histórico apagado no JSON
- ✅ Dashboard atualiza em tempo real
- ✅ Novos usuários veem estado limpo

---

## Testes em Produção (Render)

### Setup Inicial

**Pré-requisito:** Projeto já foi feito push para GitHub e conectado ao Render.

**URL:** https://chat-distribuido-m46j.onrender.com

### Teste 1: Conexão Básica (Produção)

**Passos:**

1. Abra em navegador:
   ```
   https://chat-distribuido-m46j.onrender.com
   ```

2. Aba 1: Username "alice" → Conectar
3. Aba 2: Username "bob" → Conectar

4. Aba 1: Digite "Oi do Render!"
5. Aba 2: Verifica se vê `[alice]: Oi do Render!`

**Esperado:**
- ✅ Página carrega rápido (cdn)
- ✅ Ambas conectam em < 2s
- ✅ Mensagens aparecem em tempo real
- ✅ Dashboard mostra dados do servidor remoto

**Checklist:**
- ✅ Sem erros de CORS (Socket.IO configurado)
- ✅ Sem erros de SSL (HTTPS)
- ✅ Sem erros de porta (5001 exposto via Render)

---

### Teste 2: Failover em Produção (Com Logs)

**Importante:** Antes de testar, resetar o estado:

```bash
# Windows (PowerShell):
Invoke-WebRequest -Uri "https://chat-distribuido-m46j.onrender.com/demo/reset-failover-history" -Method POST

# Linux/Mac:
curl -X POST https://chat-distribuido-m46j.onrender.com/demo/reset-failover-history
```

Isso garante que sistema começa no estado `Primary`.

**Passos:**

1. Abra Render Dashboard em outra janela:
   ```
   https://dashboard.render.com → Selecione serviço "chat-distribuido"
   ```

2. Abra chat em 2 abas:
   ```
   https://chat-distribuido-m46j.onrender.com
   Aba 1: "alice"
   Aba 2: "bob"
   ```

3. Conecte ambos e comece a trocar mensagens

4. Abra terminal e execute:
```bash
# Windows:
Invoke-WebRequest -Uri "https://chat-distribuido-m46j.onrender.com/demo/kill-engine" -Method POST

# Linux/Mac:
curl -X POST https://chat-distribuido-m46j.onrender.com/demo/kill-engine
```

5. Observe simultâneamente:
   - **Render Logs:**
     ```
     [DEMO] SIMULATING ENGINE FAILURE - Killing all TCP connections
     [DEMO] Killed N connections
     
     [Após ~2s]
     Servidor principal indisponível. Assumindo controle...
     Chat Engine iniciado em 127.0.0.1:5000
     [gateway.tcp_proxy] Reconectado após falha
     ```
   - **Abas do navegador:**
     - Breve congelamento
     - Banner: `⚠️ SERVIDOR MUDOU PARA BACKUP`
     - Dashboard atualiza
     - Mensagens continuam funcionando

6. Teste mensagens post-failover:
   - Aba 1 (alice): "Olá após failover!"
   - Aba 2 (bob): Vê a mensagem
   - Aba 2 (bob): "Funcionou!"
   - Aba 1 (alice): Vê a mensagem

**Checklist:**
- ✅ Failover detectado em ~2-3 segundos
- ✅ Sem perda de conexão WebSocket
- ✅ Chat continua funcionando
- ✅ Histórico de failover registrado
- ✅ Usuários não precisam reconectar manualmente

---

### Teste 3: Carga com Múltiplos Usuários (Produção)

**Objetivo:** Verificar comportamento com 5-10 usuários

**Passos:**

1. Abra 5-10 abas do navegador
2. Conecte cada uma com username diferente:
   - alice, bob, charlie, diana, evan, frank, grace, henry, iris, jack

3. Todos simultaneamente enviam mensagens:
   - Cada um envia 2-3 mensagens
   - Observe se todas aparecem em tempo real
   - Observe se a ordem é mantida

4. Verifique dashboard:
   - "USUÁRIOS CONECTADOS: 10"
   - Lista completa de todos os nomes

5. Execute failover:
```bash
curl -X POST https://chat-distribuido-m46j.onrender.com/demo/kill-engine
```

6. Observe:
   - Todas as 10 abas permanecem conectadas (exceto breve reconexão)
   - Todas conseguem enviar/receber após failover
   - Nenhuma desconexão indesejada

**Checklist:**
- ✅ 10 conexões simultâneas funcionam
- ✅ Broadcast atinge todos
- ✅ Failover não desconecta clientes
- ✅ Performance aceitável (< 200ms latência)

---

## Testes de Resiliência e Failover

### Cenário 1: Failover Automático (Backup Assume)

**Como testar:**
```bash
curl -X POST http://localhost:5001/demo/kill-engine
```

**O que testamos:**
- Heartbeat monitor detecta falha
- Backup sobe rapidamente
- Usuários reconectam
- Chat continua funcionando

**Resultado esperado:** ✅ Falha recuperada em ~2-3s

---

### Cenário 2: Múltiplos Failovers Consecutivos

**Passos:**

1. Failover 1:
```bash
curl -X POST http://localhost:5001/demo/kill-engine
# Espere 3 segundos
```

2. Dashboard deve mostrar:
   - `SERVIDOR: Backup`
   - `ÚLTIMO FAILOVER: timestamp-1`

3. Failover 2:
```bash
curl -X POST http://localhost:5001/demo/kill-engine
# Espere 3 segundos
```

4. Dashboard deve mostrar:
   - `SERVIDOR: Backup` (ou possível Primary swap, dependendo da lógica)
   - `ÚLTIMO FAILOVER: timestamp-2` ← atualizado

**O que testamos:**
- Failover múltiplo não quebra o sistema
- Histórico é atualizado corretamente
- Sem efeitos colaterais de estado stale

---

### Cenário 3: Reconexão Gradual de Usuários

**Objetivo:** Simular perda de conexão de UM usuário, não de todo o engine

**Como testar (via browser DevTools):**

1. Aba 1 (alice): Abra DevTools (F12)
2. Network → Disconnect (simula perda de rede)
3. Observe:
   - Aba 1: Vê "Conexão perdida..."
   - Aba 2 (bob): Continua funcionando normalmente
   - Alice sai da lista de "USUÁRIOS CONECTADOS"

4. Network → Reconnect
5. Observe:
   - Aba 1: Reconecta automaticamente
   - Lista atualiza: alice reaparece
   - Consegue enviar/receber mensagens

**Checklist:**
- ✅ Desconexão de 1 usuário não afeta outros
- ✅ Reconexão automática funciona
- ✅ Estado sincroniza corretamente

---

## Testes de Segurança

### Validação de Username

**Como testar:**
```python
# Via Python socket (veja seção Teste 3 de testes locais)
# Testa regex validation do engine
```

**Protege contra:**
- SQL injection (não há DB, mas valida entrada)
- Command injection (socket protocol simples)
- XSS (frontend escapa HTML)

---

### Proteção contra Health Checks HTTP

**Objetivo:** Engine TCP não responde a probes HTTP diretos

**Como testar:**
```bash
# Tenta fazer HTTP request direto para TCP server (deve falhar)
curl -v http://localhost:5000/

# Deve dar erro tipo:
# "HTTP/1.0 400 Bad Request"
# Ou simplesmente fechar a conexão
```

**Por quê:** Engine é TCP puro, não HTTP. Se alguém tentar HTTP, é rejeitado.

**Teste no código:**
```python
# backend/chat_engine/protocol.py → is_http_probe()
import socket
s = socket.socket()
s.connect(('127.0.0.1', 5000))
s.sendall(b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n")
response = s.recv(1024)
print(response)  # Deve ser vazio ou erro
s.close()
```

---

## Troubleshooting

### Problema: "Connection refused" ao conectar

**Possível causa:** Engine não está rodando

**Solução:**
```bash
# Terminal 1
python backend/chat_engine.py
# Deve mostrar: "Chat Engine iniciado..."

# Verifique porta
# Windows:
netstat -ano | findstr :5000

# Linux/Mac:
ss -ltnp | grep 5000
```

---

### Problema: "Port already in use"

**Possível causa:** Engine anterior não foi fechado

**Solução:**
```bash
# Windows:
netstat -ano | findstr :5000
# Identifique o PID, depois:
taskkill /PID <PID> /F

# Linux/Mac:
lsof -i :5000
kill -9 <PID>
```

---

### Problema: Dashboard não atualiza depois de failover

**Possível causa:** Cache do navegador

**Solução:**
```bash
# Hard refresh
# Windows/Linux: Ctrl + Shift + R
# Mac: Cmd + Shift + R

# Ou abra DevTools → Network → desmarque "Disable cache" → recarregue
```

---

### Problema: Failover não ocorre (backup não assume)

**Possível causa:** `backup_server.py` não está rodando

**Solução:**
```bash
# Terminal 2
python backend/backup_server.py
# Deve mostrar: "Backup server monitorando..."

# Se ainda não funcionar, verifique logs:
# Procure por "Heartbeat" para confirmar monitoramento ativo
```

---

### Problema: Mensagens não chegam a todos os usuários

**Possível causa:** Gateway não está fazendo broadcast corretamente

**Solução:**
```bash
# 1. Verifique quantos usuários estão em clients_map:
#    Terminal 3 (gateway) deve mostrar logs de join/disconnect

# 2. Verifique firewall:
netstat -ano | findstr :5001
# Deve estar LISTENING

# 3. Verifique CORS no navegador:
# DevTools → Console → procure por mensagens de CORS
```

---

## FAQ

### P1: "Por que o Backup aparece como 'ativo' logo na conexão?"

**R:** O arquivo `backend/.runtime/system_status.json` persiste entre execuções. Se a última execução terminou com `role: "backup"`, a próxima herda esse estado.

**Solução:** Execute antes do teste:
```bash
# Windows:
.\reset_state.ps1
# Linux/Mac:
./reset_state.sh
```

Isso reseta o arquivo e garante `role: "primary"` inicial.

---

### P2: "Quantas mensagens podem ser armazenadas?"

**R:** O sistema **não armazena mensagens** em persistência. São apenas passadas em tempo real. Se um usuário se desconectar, não vê mensagens antigas. Para histórico, precisaríamos de um banco de dados.

---

### P3: "E se o Backup cair também?"

**R:** Atualmente o sistema espera que pelo menos o Primary ou Backup estejam rodando. Se ambos caem:
- Gateway continua WebSocket-active para navegadores (mas não consegue conectar ao engine)
- Usuários veem "Servidor indisponível"
- Precisaria de manual restart de um dos engines

(Melhoria futura: 3º monitor ou restart automático)

---

### P4: "Posso usar em produção (Render) sem preocupações?"

**R:** Para demonstração acadêmica: **Sim, está estável.** Para produção real:
- ⚠️ Sem persistência de dados
- ⚠️ Sem autenticação
- ⚠️ Sem rate limiting
- ✅ Com resiliência (failover automático)
- ✅ Com monitoramento básico

---

### P5: "Como monitoro a saúde do sistema?"

**R:** Via logs e endpoints:

```bash
# Health check básico
curl https://chat-distribuido-m46j.onrender.com/health

# Ver logs em tempo real (Render Dashboard)
# Service → Logs → tail -f

# Ver estado do sistema
curl https://chat-distribuido-m46j.onrender.com/status
```

---

## Resumo de Testes

| Teste | Local | Render | Status |
|-------|-------|--------|--------|
| Login e Chat | ✅ | ✅ | Funcionando |
| Failover Automático | ✅ | ✅ | Funcionando |
| Múltiplos Usuários | ✅ | ✅ | Funcionando |
| Telemetria/Dashboard | ✅ | ✅ | Funcionando |
| Validação de Username | ✅ | ✅ | Funcionando |
| Histórico de Failover | ✅ | ✅ | Funcionando |
| Reset de Estado | ✅ | ✅ | Funcionando |

---

**Último update:** 2026-05-18  
**Desenvolvido por:** André (Sistemas Distribuídos)
