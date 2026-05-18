# 🧪 Guia de Testes - Chat Distribuído

Este documento descreve como testar:
1. **Tolerância a falhas** (failover automático do backup server)
2. **Proteção contra ataques** (validação de entrada, filtering de probes)
3. **Comunicação multi-usuário sem interrupção**

---

## 1️⃣ Teste de Failover do Servidor Backup

### Objetivo
Demonstrar que quando o servidor principal cai, o backup assume automaticamente sem afetar os usuários conectados.

---

### ⭐ **Teste no RENDER (Produção) - Recomendado para Apresentação**

#### Setup

1. **Abra o chat em produção:**
   - Navegador: https://chat-distribuido-m46j.onrender.com
   - Conecte 2-3 usuários em abas diferentes

2. **Prepare o Dashboard do Render:**
   - Acesse https://dashboard.render.com
   - Vá para seu serviço "chat-distribuido-m46j"
   - Deixe visível em outra janela/monitor

#### Execução do Teste

**Passo 1:** Conectar usuários
- Aba 1: Username "andre"
- Aba 2: Username "dalmazo"
- Ambos trocando mensagens normalmente
- Verifique os logs do Render em tempo real

**Passo 2:** Simular falha usando o endpoint Demo

Abra **um novo terminal PowerShell** e execute:

```powershell
# No Render (em produção)
Invoke-WebRequest -Uri "https://chat-distribuido-m46j.onrender.com/demo/kill-engine" -Method POST

# Ou se preferir, via curl
curl -X POST https://chat-distribuido-m46j.onrender.com/demo/kill-engine
```

**O que esse comando faz:**
- Mata APENAS as conexões TCP com o engine
- Deixa o backup server rodando
- Backup detecta a falha (heartbeat)
- Backup assume a porta 5000
- Usuários reconectam automaticamente

**Passo 3:** Observar comportamento

**Esperado nos LOGS (Render Dashboard):**
```
[DEMO] SIMULATING ENGINE FAILURE - Killing all TCP connections
[DEMO] Closing TCP connection for sid1
[DEMO] Closing TCP connection for sid2
[DEMO] Killed 2 connections. Backup should take over in ~2 seconds.

Servidor principal indisponível. Assumindo controle...
Backup assumindo a porta 5000
Chat Engine iniciado em 127.0.0.1:5000
```

**Esperado no NAVEGADOR:**
```
⏸️ Conexão pode interromper por 2-3 segundos
✅ Usuários A e B RECONECTAM automaticamente
✅ Conseguem enviar e receber mensagens normalmente
✅ Nenhuma mensagem foi perdida
```

**Tempo de failover:** ~2-3 segundos (rápido e imperceptível)

---

### 🏠 **Teste LOCALMENTE (Desenvolvimento) - Para Debug**

Se preferir testar no seu PC antes:

```bash
# Terminal 1: Chat Engine Principal
python backend/chat_engine.py

# Terminal 2: Backup Server (fica observando)
python backend/backup_server.py

# Terminal 3: Web Gateway
python backend/web_gateway.py

# Navegador: Abra http://localhost:5001
# Conecte 2-3 usuários diferentes
```

**Passo 1:** Conectar usuários
- Usuário A: "andre"
- Usuário B: "dalmazo"
- Ambos trocando mensagens normalmente

**Passo 2:** Simular falha usando o endpoint Demo (Terminal 4)

```powershell
# Terminal 4 (PowerShell)
Invoke-WebRequest -Uri "http://localhost:5001/demo/kill-engine" -Method POST

# Ou via curl (se tiver instalado)
curl -X POST http://localhost:5001/demo/kill-engine
```

**Passo 3:** Observar comportamento

**Esperado:**
```
[Terminal 2 - Backup Server]
Servidor principal indisponível. Assumindo controle...
Backup assumindo a porta 5000
Chat Engine iniciado em 127.0.0.1:5000

[Navegador]
✅ Usuários A e B RECONECTAM automaticamente
✅ Conseguem enviar e receber mensagens normalmente
✅ Nenhuma mensagem foi perdida
```

**Por que funciona:**
- `backup_server.py` faz healthcheck a cada 2 segundos
- Detecta a falha do engine principal
- Sobe um novo `ChatEngine` na mesma porta 5000
- Web Gateway reconecta automaticamente (já tem retry logic)
- Usuários não percebem a falha

---

## 2️⃣ Testes de Proteção Contra Ataques

### 2.1 - Rejeição de Username Inválido

**O que testa:** Validação regex de username

```python
# Terminal Python separado
import socket

def test_invalid_username(username, description):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('127.0.0.1', 5000))
        s.sendall(username.encode('utf-8'))
        response = s.recv(1024)
        print(f"✓ {description}: {response.decode()}")
        s.close()
    except Exception as e:
        print(f"✗ {description}: {e}")

# Testes
test_invalid_username("andre123", "Username VÁLIDO (alfanumérico)")
test_invalid_username("andre@123", "Username INVÁLIDO (contém @)")
test_invalid_username("a" * 25, "Username INVÁLIDO (muito longo, >20 chars)")
test_invalid_username("", "Username INVÁLIDO (vazio)")
```

**Esperado:**
- `andre123` → Aceito ✅
- `andre@123` → Rejeitado (mensagem "Invalid username") ❌
- `a` * 25 → Rejeitado ❌
- `""` → Rejeitado ❌

### 2.2 - Rejeição de HTTP Methods como Username

**O que testa:** Detecção de probes HTTP (GET, HEAD, POST, etc)

```python
def test_http_method_as_username():
    http_methods = ["GET", "HEAD", "POST", "PUT", "DELETE", "OPTIONS"]
    
    for method in http_methods:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('127.0.0.1', 5000))
        s.sendall(method.encode('utf-8'))
        response = s.recv(1024)
        print(f"  {method}: {response.decode().strip()}")
        s.close()

test_http_method_as_username()
```

**Esperado:** Todos retornam `Invalid username` ❌

### 2.3 - Filtragem de Mensagens HTTP no Gateway

**O que testa:** Gateway filtra probes antes de chegar ao cliente web

**Verificação nos logs:**
```bash
# Procure por linhas como:
# "Ignorando mensagem de probe HTTP vinda do Engine: ..."

# Isso significa: mesmo que algum probe chegue ao engine,
# o gateway o filtra antes de emitir ao navegador.
```

---

## 3️⃣ Teste de Comunicação Multi-Usuário

### Objetivo
Demonstrar que múltiplos usuários conversam simultaneamente sem interferências.

### Setup
```bash
# Abra 3-4 abas diferentes em http://localhost:5001 ou https://chat-distribuido-m46j.onrender.com
# Conecte com nomes diferentes:
# - Aba 1: "user1"
# - Aba 2: "user2"
# - Aba 3: "user3"
```

### Execução
1. user1 envia: "Olá pessoal!"
2. user2 envia: "Oi user1!"
3. user3 envia: "Tudo bem?"
4. user1 envia: "Tudo certo!"

**Esperado:**
- Todas as mensagens aparecem em TODAS as abas
- Nenhuma mensagem é perdida
- Ordem está correta
- IDs de usuários estão corretos

**O que está sendo testado:**
- ✅ Cada cliente tem sua própria thread
- ✅ Broadcast funciona corretamente
- ✅ Lock previne race conditions
- ✅ Gateway proxifica corretamente WebSocket → TCP → WebSocket

---

## 4️⃣ Teste de Tolerância a Falhas (Avançado)

### Objetivo
Testar o comportamento quando a conexão é quebrada abruptamente.

### Setup
```bash
# Conecte um usuário ao chat
# Enquanto está conversando, desligue a conexão (simule)

# Formas de simular:
# - Feche a aba do navegador
# - Apague o cabo de rede (localhost: não funciona, mas em produção...)
# - Força fechamento do browser
```

### Esperado
- Log do gateway: `[{sid}] Cliente desconectando`
- Mensagem no chat: `[SYSTEM] username saiu do chat.`
- Outros usuários veem a saída
- Nenhum crash no servidor

---

## 5️⃣ Teste de Desempenho (Opcional)

### Flood de Conexões

```python
import socket
import threading
import time

def connect_and_spam(username, num_messages):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('127.0.0.1', 5000))
        s.sendall(username.encode('utf-8'))
        
        for i in range(num_messages):
            s.sendall(f"Mensagem {i}\n".encode('utf-8'))
            time.sleep(0.1)  # 100ms entre mensagens
        
        s.close()
    except Exception as e:
        print(f"Erro em {username}: {e}")

# Cria 10 usuários com 20 mensagens cada
threads = []
for i in range(10):
    t = threading.Thread(target=connect_and_spam, args=(f"user{i}", 20))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

print("Teste de desempenho concluído!")
```

**Esperado:**
- Servidor não trava
- Todas as mensagens são entregues
- Logs mostram threading ativo

---

## 📊 Resumo de Implementações Testadas

| Funcionalidade | Arquivo | Linha |
|---|---|---|
| Validação de username | `chat_engine.py` | ~195 |
| Rejeição de HTTP methods | `chat_engine.py` | ~205 |
| Healthcheck ignorado | `chat_engine.py` | ~192 |
| Lock para thread-safety | `chat_engine.py` | ~217 |
| Broadcast thread-safe | `chat_engine.py` | ~280 |
| Failover automático | `backup_server.py` | ~45 |
| Monitoramento heartbeat | `backup_server.py` | ~37 |
| Filtro de probes HTTP | `web_gateway.py` | ~150 |

---

## 🎯 Checklist para Apresentação

- [ ] Teste 1: Iniciar os 3 servidores
- [ ] Teste 2: Conectar 2-3 usuários
- [ ] Teste 3: Trocar mensagens (demonstrar comunicação)
- [ ] Teste 4: Matar o engine principal (Ctrl+C)
- [ ] Teste 5: Verificar que backup assumiu (logs)
- [ ] Teste 6: Verificar que usuários continuam conectados
- [ ] Teste 7: Enviar mais mensagens (demonstrar continuidade)
- [ ] Teste 8: Rejeitar username inválido (script Python)
- [ ] Teste 9: Rejeitar HTTP method como username

---

## 💡 Dicas para Apresentação

1. **Faça os testes em ordem:** Comece com os mais simples (testes 1-3)
2. **Prepare os terminais com antecedência:** Tenha 3-4 terminais prontos
3. **Use navegadores diferentes:** Firefox, Chrome, Edge → mostra que funciona em qualquer browser
4. **Salve prints de logs:** Tire screenshots dos logs mostrando failover
5. **Explique o que está acontecendo:** "Agora vou matar o engine e o backup vai assumir..."

---

**Última atualização:** 2026-05-18
**Status:** Pronto para apresentação
