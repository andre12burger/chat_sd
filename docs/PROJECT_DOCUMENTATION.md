# Documentação Completa do Projeto — Chat Distribuído

Este documento unificado descreve o projeto em detalhes: árvore de arquivos, responsabilidades de cada módulo, instruções completas de uso local e produção, endpoints, scripts, procedimentos de teste e troubleshooting.

URL pública (produção): https://chat-distribuido-m46j.onrender.com

----

## 1. Visão Geral

Projeto acadêmico demonstrando comunicação cliente-servidor usando sockets TCP e um gateway WebSocket. Arquitetura em três camadas:
- Navegador (cliente web) — `frontend/` (HTML/CSS/JS)
- Web Gateway — `backend/gateway` (Flask + Flask-SocketIO) que faz proxy WebSocket ↔ TCP
- Chat Engine — `backend/chat_engine` (servidor TCP puro, thread-per-client)

Há também um componente de backup/monitor para failover automático: `backend/backup/`.

----

## 2. Árvore de arquivos (resumo)

```
Chat_SD/
├── README.md                      # Resumo e Quick Start (top-level)
├── requirements.txt               # Dependências Python
├── start.sh                       # Start script (Linux/Render)
├── run.bat / run.ps1              # Scripts Windows auxiliares
├── reset_state.*                  # Scripts para resetar system status
├── frontend/
│   ├── index.html                 # UI (MSN-like)
│   ├── client_app.js              # Lógica do cliente (Socket.IO)
│   └── style.css                  # Estilos
├── backend/
│   ├── chat_engine.py             # Entry point -> importa package chat_engine
│   ├── web_gateway.py             # Entry point -> importa gateway.run_app
│   ├── backup_server.py           # Entry point -> inicia BackupServer
│   ├── runtime_status.py          # Persistência de estado (.runtime/system_status.json)
│   ├── backup/                    # Monitor/Failover
│   │   └── monitor.py             # BackupServer (heartbeat, become_primary)
│   └── gateway/                   # Gateway modular
│       ├── app.py                 # Flask app, rotas, monitor de sistema
│       ├── socket_handlers.py     # Handlers Socket.IO (join/send/disconnect)
│       ├── tcp_proxy.py           # ClientTCPConnection (TCP lifecycle + reader)
│       └── app_context.py         # ponte para o SocketIO global
└── docs/                          # Documentação
    ├── PROJECT_DOCUMENTATION.md   # (este arquivo)
    ├── SETUP.md                   # Instruções detalhadas de setup
    ├── DEPLOY.md                  # Deploy no Render + UptimeRobot
    └── TESTING_GUIDE.md           # Guia de testes e passos reproduzíveis
```

----

## 3. O que cada arquivo/folder faz (detalhado)

- `frontend/index.html` — Interface do chat (login, painel de telemetria, chat area). Usada em apresentações.
- `frontend/client_app.js` — Lógica do cliente: conexão Socket.IO, renderização do dashboard, handlers de eventos (`system_state`, `server_change`, `receive_message`), UI helpers. Contém a lógica de telemetria que atualiza o dashboard.
- `frontend/style.css` — Estilos; contém tema Luna (Windows XP-like). Atualmente há regras que ocultam a telemetria para apresentação (modo simplificado).

- `backend/chat_engine.py` — Entry point. Cria instância de `ChatEngine` (do package `backend/chat_engine/`). Mantém a separação entre entry-point e implementação.
- `backend/chat_engine/`:
  - `server.py` — Implementação do `ChatEngine`: socket server, `threading.Thread` por cliente, `threading.Lock` para sincronização, broadcast de mensagens. Atualiza `runtime_status` ao subir/parar.
  - `protocol.py` — Helpers para validação de `username`, detecção de probes HTTP e constantes (ex.: `HEALTHCHECK_USERNAME`).

- `backend/web_gateway.py` — Entry point. Importa `gateway.run_app` e inicia Flask/SocketIO.
- `backend/gateway/`:
  - `app.py` — Configura Flask + SocketIO, inicia o `SystemMonitor` que emite `system_state` periodicamente e implementa endpoints demo (`/demo/kill-engine`, `/demo/reset-failover-history`).
  - `socket_handlers.py` — Eventos Socket.IO: `join_chat`, `send_message`, `disconnect`. Mantém mapa `clients_map` (sid → `ClientTCPConnection`).
  - `tcp_proxy.py` — Classe `ClientTCPConnection`: gerencia socket TCP como cliente do engine, thread leitor, reconexão automática, parsing de mensagens `__SYSTEM_INFO__ ...` e reemissão por SocketIO. Aqui foi adicionada emissão de `system_state` ao reconectar (para atualizar frontends).
  - `app_context.py` — Armazena instância global de `socketio` para uso por outros módulos (evita import circular).

- `backend/backup_server.py` — Entry point para o serviço de monitor/backup.
- `backend/backup/monitor.py` — `BackupServer`: realiza heartbeat para o primário; em caso de falha escreve `runtime_status` com `last_failover_*` e sobe nova instância de `ChatEngine` como backup assumindo a porta 5000.

- `backend/runtime_status.py` — Módulo leve para leitura/gravação atômica de `backend/.runtime/system_status.json`. Fornece `read_system_status()` e `write_system_status(...)`. Mantém campos `last_failover_reason` e `last_failover_at`.

- `start.sh` / `run.ps1` / `run.bat` — Scripts para iniciar os processos localmente (entry-points). `start.sh` é usado pelo Render como start command e executa os três entry points.

- `reset_state.ps1` / `reset_state.sh` — Scripts adicionados para resetar `system_status.json` antes de demonstração para garantir estado `primary` inicial.

- `docs/` — Contém a documentação (setup, deploy, testes, arquitetura). Agora consolidada.

----

## 4. Endpoints e eventos importantes

HTTP endpoints (Gateway):
- `GET /` → serve `index.html`
- `POST /demo/kill-engine` → simula falha matando conexões TCP (test)
- `POST /demo/reset-failover-history` → reseta campos `last_failover_*` no arquivo de status
- `GET /health` → healthcheck (Render/loadbalancer)

Socket.IO events (Gateway ↔ Client):
- Client → Gateway:
  - `join_chat` { username }
  - `send_message` { message }
- Gateway → Client:
  - `connection_success`
  - `connection_error`
  - `receive_message` { message }
  - `system_state` { ... }  (periodic + emit on reconnection)
  - `server_change` { server_role, server_label, message }

TCP protocol (Gateway ↔ Engine):
- Handshake: client sends username\n
- Engine sends: "Bem-vindo ao chat!" + optional `__SYSTEM_INFO__ {json}` messages
- Messages: plain text lines terminated with \n
----

## 5. Como usar o repositório (absolutamente completo)

### 5.1 Requisitos
- Python 3.10+
- pip (ou ambiente Conda)

Recomendação: use `venv` ou `conda`.

### 5.2 Instalar dependências

```bash
# Unix
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 5.3 Configurar (opcional)
- Antes de demonstração, rode o script de reset para garantir `Primary` inicial:

```bash
# Unix
./reset_state.sh
# Windows (PowerShell)
.\reset_state.ps1
```

### 5.4 Rodar localmente (modo dev)
Abra 3 terminais:

Terminal 1 — chat engine (Primary):

```bash
python backend/chat_engine.py
```

Terminal 2 — backup monitor (opcional):

```bash
python backend/backup_server.py
```

Terminal 3 — web gateway:

```bash
python backend/web_gateway.py
```

Abra no navegador:
```
http://localhost:5001
```

Conecte 2-3 abas e teste troca de mensagens.

### 5.5 Rodar em produção (Render)
- Push para GitHub e conecte ao Render. Use `start.sh` como start command (já documentado em `docs/DEPLOY.md`). A URL de produção do deploy atual é:

https://chat-distribuido-m46j.onrender.com

### 5.6 Endpoints úteis para demonstração
- Simular failover:
```bash
curl -X POST https://chat-distribuido-m46j.onrender.com/demo/kill-engine
```
- Resetar histórico de failover:
```bash
curl -X POST https://chat-distribuido-m46j.onrender.com/demo/reset-failover-history
```

----

## 6. Testes e checklist (resumo)

- 3 abas conectadas → trocar mensagens: todas veem as mensagens
- Ver logs do `chat_engine` mostrando `ClientThread-...` (thread-per-client)
- Executar `/demo/kill-engine` → observar backup assumir em ~2-3s e frontends reconectarem
- Verificar `system_state` e `server_change` sendo emitidos

Para um guia **completo e exhaustivo** de testes (tudo que o usuário vê, como foi implementado, testes locais e em produção, comandos de demonstração), consulte `docs/TESTING_COMPLETE.md`.

----

## 7. Limpeza e arquivos seguros para remover (após revisão)
- `docs/ESTRUTURA.md` — duplicata/overlap com docs existentes (será removido)
- `docs/REFATORACAO.md` — histórico de refatoração (conteúdo incorporado)
- `docs/QUICK_START.txt` — duplicata curta do README
- `test_imports.py` — script auxiliar de verificação (opcional)

> Nota: arquivos com instruções de deploy/teste foram preservados e consolidados. Se quiser que eu remova os itens listados acima, faço a exclusão e commito.

----

## 8. Troubleshooting (comandos práticos)

- Verificar portas:

```bash
# Unix
ss -ltnp | grep 5000
# Windows (PowerShell)
netstat -ano | findstr :5001
```

- Forçar reset do state:
```bash
rm backend/.runtime/system_status.json || true
```

- Ver logs no Render: Dashboard → Service → Logs

----

## 9. Próximos passos sugeridos
- (Opcional) Remover código de telemetria da UI se não for usado e simplificar `client_app.js`.
- Adicionar testes automatizados (unit + integration) para `protocol.validate_username` e `tcp_proxy` behaviors.
- Adicionar `Makefile` ou `invoke` tasks para comandos comuns (setup, start, test).

----

## 10. Créditos
Desenvolvido para a disciplina de Sistemas Distribuídos (Prof. Bruno Dalmazo).


---

**Documento gerado automaticamente por assistente; confirme as remoções desejadas antes de prosseguir.**
