# Chat Multiusuário - Projeto de Sistemas Distribuídos

## Visão Geral

Sistema de chat multiusuário cliente-servidor desenvolvido para a disciplina de **Sistemas Distribuídos** (Prof. Bruno Dalmazo).

O projeto demonstra:
# Chat Multiusuário - Chat Distribuído

Versão concisa e prática para uso e apresentação. Link de demonstração pública:

https://chat-distribuido-m46j.onrender.com

Este repositório implementa um chat multiusuário com:
- Motor TCP puro (`chat_engine`) com thread-per-client
- Gateway Web (Flask + Socket.IO) que faz proxy WebSocket ↔ TCP
- Backup/monitor com failover automático

Para documentação completa e detalhada (arquitetura, árvore, comandos, testes), consulte:

- `docs/PROJECT_DOCUMENTATION.md` (documentação unificada)
- `docs/SETUP.md` (setup do ambiente)
- `docs/DEPLOY.md` (deploy no Render)
- `docs/TESTING_GUIDE.md` (roteiro de testes)
- `docs/apresentacao/` (roteiro e perguntas prontas para a defesa)

Quick start (local)

1. Crie e ative um virtualenv:

```bash
python -m venv .venv
# Unix
source .venv/bin/activate
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

2. Instale dependências:

```bash
pip install -r requirements.txt
```

3. Abra 3 terminais e rode (na ordem preferida):

```bash
# Terminal 1
python backend/chat_engine.py

# Terminal 2 (opcional - monitor/backup)
python backend/backup_server.py

# Terminal 3
python backend/web_gateway.py
```

4. Abra o navegador em `http://localhost:5001` e conecte 2-3 abas.

Comandos úteis (produção):

```bash
# Simular failover (provação)
curl -X POST https://chat-distribuido-m46j.onrender.com/demo/kill-engine

# Resetar histórico de failover
curl -X POST https://chat-distribuido-m46j.onrender.com/demo/reset-failover-history
```

Se quiser a documentação completa (arquitetura, árvore de arquivos, comandos, troubleshooting), abra `docs/PROJECT_DOCUMENTATION.md`.

---

**Última atualização:** 17 de maio de 2026
