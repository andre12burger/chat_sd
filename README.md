# Chat Multiusuário - Projeto de Sistemas Distribuídos

## Visão Geral

Sistema de chat multiusuário cliente-servidor desenvolvido para a disciplina de **Sistemas Distribuídos** (Prof. Bruno Dalmazo).

O projeto demonstra:
- ✅ Comunicação simultânea entre múltiplos usuários via servidor central
- ✅ Uso explícito de **sockets TCP** para comunicação inter-processo
- ✅ Instanciação manual de **threading.Thread** para cada cliente
- ✅ Sincronização thread-safe com **threading.Lock**
- ✅ Interface web via navegador (HTML/JS/WebSocket)

## Arquitetura

```
┌─────────────────────────────────────────────────────┐
│                    Navegador (Usuário)               │
│              HTML/JS/WebSocket Client                │
└────────────────────────┬────────────────────────────┘
                         │ WebSocket (Port 5001)
                         ▼
┌─────────────────────────────────────────────────────┐
│         web_gateway.py (Flask + Flask-SocketIO)      │
│      ✓ Serve index.html                             │
│      ✓ Proxy bidirecional TCP <-> WebSocket         │
└──────────────┬──────────────────────────────────────┘
               │ TCP (localhost:5000)
               ▼
┌─────────────────────────────────────────────────────┐
│     chat_engine.py (Motor de Chat - CORE)           │
│  ✓ Socket TCP puro                                  │
│  ✓ Threading.Thread explícito por cliente           │
│  ✓ Sincronização com Lock                           │
│  ✓ Broadcast thread-safe                            │
└─────────────────────────────────────────────────────┘
```

## Estrutura de Arquivos

```
Chat_SD/
├── backend/
│   ├── chat_engine.py        # Motor principal (Threads + Sockets)
│   ├── web_gateway.py        # Proxy HTTP/WebSocket -> TCP
│   └── backup_server.py      # (Futuro: Servidor de backup)
├── frontend/
│   ├── index.html            # Interface do usuário
│   ├── style.css             # Estilos
│   └── client_app.js         # Lógica do cliente (WebSocket)
├── docs/
│   └── arquitetura.md        # Documentação técnica detalhada
├── requirements.txt          # Dependências Python
└── README.md                 # Este arquivo
```

## Instalação

### Pré-requisitos
- Python 3.8+
- pip

### Passos

1. Clone ou baixe o projeto:
```bash
cd Chat_SD
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

## Execução

### Terminal 1: Inicie o Chat Engine
```bash
python backend/chat_engine.py
```
Esperado:
```
2026-05-17 14:22:10,123 - [MainThread] - Chat Engine iniciado em 0.0.0.0:5000
```

### Terminal 2: Inicie o Web Gateway
```bash
python backend/web_gateway.py
```
Esperado:
```
 * Running on http://0.0.0.0:5001
 * WARNING: Do not use the development server in a production environment.
```

### Browser: Abra a interface
Navegue para: **http://localhost:5001**

## Deploy Online Gratuito

A forma mais simples para a apresentação é publicar o projeto no **Render** usando o arquivo [render.yaml](render.yaml).

### Passo a passo resumido
1. Faça push do projeto para um repositório público no GitHub.
2. No Render, escolha **New > Blueprint** e selecione o repositório.
3. O Render usará o [render.yaml](render.yaml) para instalar dependências e iniciar o serviço.
4. Após o deploy, você receberá uma URL pública do tipo `https://...onrender.com`.

### Observação importante
O deploy gratuito pode entrar em modo de suspensão quando ficar sem uso. Para a apresentação, mantenha a URL aberta antes da demonstração e, se necessário, use um monitor gratuito como o UptimeRobot para manter o serviço acordado.

### Fluxo de produção
No ambiente online, o [start.sh](start.sh) sobe três processos:
- `chat_engine.py` como motor TCP principal;
- `backup_server.py` como monitor de failover;
- `web_gateway.py` como interface web pública.

## Conceitos-Chave Implementados

### 1. **Threading.Thread Explícito**
No `chat_engine.py`, cada cliente conectado dispara uma nova thread:
```python
client_thread = threading.Thread(
    target=self.handle_client,
    args=(client_socket, client_address),
    name=f"ClientThread-{client_address[1]}"
)
client_thread.start()  # Requisito obrigatório da disciplina
```

### 2. **Sincronização com Lock**
Protege acesso compartilhado ao dicionário de clientes:
```python
with self.clients_lock:  # Adquire lock
    if username in self.clients:
        # Seção crítica: apenas esta thread acessa self.clients
        self.clients[username] = client_socket
# Libera lock automaticamente
```

**Por que é necessário?**
Sem lock, duas threads registrando clientes simultaneamente poderiam corromper o dicionário (race condition).

### 3. **Padrão Gateway (Proxy)**
O `web_gateway.py` atua como intermediário:
- Recebe WebSocket do navegador (fácil, assincronismo automático do Flask)
- Traduz para TCP puro (comunicação com chat_engine)
- Broadcast é centralizado no Engine (modelo publisher-subscriber)

## Testes Básicos

### Teste 1: Múltiplos Clientes
1. Abra http://localhost:5001 em 2-3 abas diferentes do navegador
2. Digite um username em cada aba
3. Envie mensagens — verifique se aparecem em todas as abas

### Teste 2: Logs de Concorrência
Observe os logs do `chat_engine.py`:
```
ClientThread-54321 iniciada. Total de threads ativas: 3
Cliente registrado: alice. Total: 2
Mensagem de alice: Olá!
Thread de 127.0.0.1:54321 finalizada.
```

## Documentação Técnica

Para análise em profundidade de concorrência e thread-safety, consulte:
- [docs/arquitetura.md](docs/arquitetura.md) — Diagrama detalhado e explicações

## Relatório Acadêmico (Overleaf)

Este projeto foi desenvolvido para servir como base a um relatório técnico em LaTeX. As seções-chave para documentação:

1. **Introdução**: Requisitos de Sistemas Distribuídos
2. **Arquitetura**: Padrão Gateway + separação de responsabilidades
3. **Implementação**: Threading.Thread e threading.Lock em profundidade
4. **Testes**: Validação de concorrência
5. **Conclusão**: Aprendizados sobre IPC e comunicação síncrona

## Autores
Desenvolvido como trabalho prático da disciplina **Sistemas Distribuídos** (Prof. Bruno Dalmazo).

---

**Última atualização:** 17 de maio de 2026
