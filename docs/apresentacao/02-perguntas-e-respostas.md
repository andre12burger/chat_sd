# Perguntas e Respostas Prováveis

## Onde está a lógica principal do chat?

No motor TCP, em `backend/chat_engine/server.py`. É ali que o servidor aceita conexões, cria uma thread por cliente, registra usuários e faz broadcast.

## Onde o navegador fala com o servidor?

No gateway, em `backend/gateway/app.py` e `backend/gateway/socket_handlers.py`. O navegador usa Socket.IO/WebSocket para entrar no chat e enviar mensagens.

## Onde o gateway fala com o engine?

Em `backend/gateway/tcp_proxy.py`. A classe `ClientTCPConnection` abre o socket TCP, faz handshake, lê mensagens e reconecta quando necessário.

## Onde está a função que trata a queda do servidor?

Depende do tipo de queda:

- Queda do primário detectada pelo backup: `backend/backup/monitor.py`.
- Queda da conexão TCP do cliente com o engine: `backend/gateway/tcp_proxy.py`.
- Atualização do estado visual após a falha: `backend/gateway/app.py` e `backend/gateway/tcp_proxy.py`.

## Por que usar thread por cliente?

Porque cada conexão pode ficar bloqueada esperando mensagens sem travar as outras. Isso mantém o servidor responsivo e deixa a concorrência fácil de demonstrar.

## Por que não usar um core por usuário?

Porque o código não faz pinagem de CPU nem reserva núcleo físico. Ele cria threads; o sistema operacional distribui as threads entre os cores disponíveis.

## Por que o projeto usa lock?

Porque `self.clients` no engine e `clients_map` no gateway podem ser acessados por várias threads ao mesmo tempo. O lock evita race condition ao adicionar, remover ou iterar clientes.

## Por que existem probes HTTP no código TCP?

Porque em produção é comum algum healthcheck, load balancer ou navegador bater na porta errada. O código filtra isso para não confundir essas requisições com usernames ou mensagens válidas.

## O que eu digo se perguntarem por que escolhi TCP e não só HTTP?

Que o TCP deixa explícito o controle de conexão, leitura e reconexão, o que ajuda a demonstrar conceitos de sistemas distribuídos com clareza. O HTTP fica na borda para servir página e healthcheck, mas o núcleo do chat é TCP puro.

## O que eu digo se perguntarem por que existe `runtime_status.py`?

Que ele centraliza o estado operacional do sistema em um arquivo pequeno e simples, útil para o monitor e para o frontend lerem a mesma verdade sobre papel do servidor, failover e carimbo de atualização.

## O que eu digo se perguntarem como testar a queda do servidor?

Use o endpoint de demonstração `POST /demo/kill-engine`, documentado em `docs/TESTING_GUIDE.md`. Ele derruba as conexões TCP do engine e permite observar o failover.

## Como responder se pedirem “linha por linha”?

Diga que a documentação foi organizada por responsabilidade, não por cada vírgula do código. Para defesa oral, o que importa é explicar os blocos críticos: conexão, thread, lock, broadcast, heartbeat e reconexão.