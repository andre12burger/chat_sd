# Arquitetura e Decisões Técnicas

## 1. Pilares do projeto

- `HTTP` é usado para servir a interface, healthcheck e endpoints de demonstração.
- `WebSocket` é usado entre navegador e gateway para manter a comunicação em tempo real.
- `TCP` é usado entre gateway e chat engine para manter o núcleo simples e explícito.
- `threading.Thread` é usado para atender múltiplos clientes em paralelo.
- `threading.Lock` protege estruturas compartilhadas contra race condition.
- `runtime_status.py` guarda o estado compartilhado do sistema em disco para que o monitor e o gateway leiam a mesma fonte.

## 2. Onde isso está no código

- `backend/gateway/app.py` configura Flask, Socket.IO, healthcheck e o monitor de estado.
- `backend/gateway/socket_handlers.py` trata `join_chat`, `send_message` e `disconnect`.
- `backend/gateway/tcp_proxy.py` faz a ponte TCP, lê respostas do engine e reconecta quando o socket cai.
- `backend/chat_engine/server.py` implementa o servidor TCP com thread por cliente e broadcast.
- `backend/chat_engine/protocol.py` concentra validações e proteção contra probes HTTP.
- `backend/backup/monitor.py` detecta falha do primário e assume o controle.
- `backend/runtime_status.py` persiste o estado operacional.

## 3. Thread por usuário, não core por usuário

O projeto não reserva um núcleo físico para cada novo usuário. O que acontece é:

1. O engine cria uma `thread` para cada conexão.
2. O sistema operacional decide em qual core aquela thread será executada.
3. O `Lock` evita que duas threads alterem o mesmo dicionário ao mesmo tempo.

Isso é diferente de alocação fixa de core. O código controla concorrência de software; o escalonamento de hardware fica com o SO.

## 4. Protocolo HTTP no projeto

HTTP não é o protocolo principal do chat. Ele aparece em três situações:

- Para servir a página e arquivos estáticos no gateway.
- Para o endpoint `GET /health`, usado por monitoramento externo.
- Para detectar probes acidentais ou healthchecks que batem em porta TCP errada.

O chat em tempo real segue por WebSocket e TCP, não por HTTP tradicional.

## 5. Queda do servidor e recuperação

O comportamento de falha é dividido em camadas:

- O backup faz heartbeat no primário em `backend/backup/monitor.py`.
- Se o heartbeat falha, o backup sobe um novo engine.
- O gateway detecta socket fechado e tenta reconectar em `backend/gateway/tcp_proxy.py`.
- Depois da reconexão, o gateway reemite o estado do sistema para o frontend.

## 6. Por que essa arquitetura foi uma boa escolha

- Mantém o chat simples para explicar em sala.
- Separa responsabilidades de forma clara.
- Facilita demonstrar concorrência e falha sem esconder a lógica em frameworks complexos.
- Permite defender decisões técnicas com base em isolamento, observabilidade e tolerância a falhas.