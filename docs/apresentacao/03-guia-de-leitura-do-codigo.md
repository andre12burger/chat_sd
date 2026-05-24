# Guia de Leitura do Código

Este guia serve para localizar rapidamente as partes que normalmente viram pergunta na apresentação.

## 1. Entrada do sistema

- `backend/web_gateway.py` inicia o gateway web.
- `backend/chat_engine.py` inicia o motor TCP.
- `backend/backup_server.py` inicia o monitor de backup.

## 2. Fluxo de conexão do usuário

1. O navegador dispara `join_chat`.
2. `backend/gateway/socket_handlers.py` cria um `ClientTCPConnection`.
3. `backend/gateway/tcp_proxy.py` conecta ao engine e manda o username.
4. `backend/chat_engine/server.py` valida, registra e confirma.
5. O gateway repassa `connection_success`, `system_state` e mensagens.

## 3. Trechos que valem explicar com calma

- `backend/chat_engine/server.py`: criação de thread por cliente, lock e broadcast.
- `backend/gateway/tcp_proxy.py`: leitura em background, autenticação, reconexão e emissão de estado.
- `backend/backup/monitor.py`: heartbeat e failover.
- `backend/gateway/app.py`: healthcheck, dashboard de estado e endpoint de demo.

## 4. Como usar isso para revisar o código

Se a pergunta for “por que essa linha existe?”, a resposta costuma cair em uma destas categorias:

- segurança de entrada;
- concorrência;
- separação de responsabilidades;
- tolerância a falha;
- observabilidade;
- compatibilidade com a hospedagem.

Quando surgir uma nova dúvida, vale registrar no arquivo mais próximo do tema em vez de espalhar notas pelo repositório.