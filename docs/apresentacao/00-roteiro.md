# Roteiro Curto de Apresentação

Este projeto mostra uma arquitetura de chat distribuído em três peças principais:

- Navegador do usuário, com interface em HTML/CSS/JS.
- Gateway Web com Flask + Socket.IO, que fala WebSocket com o navegador e TCP com o motor.
- Chat Engine TCP puro, que atende cada cliente em uma thread.

### Mensagem principal que você pode defender

O projeto foi escolhido para demonstrar comunicação cliente-servidor, concorrência com threads, sincronização com lock, detecção de falha e reconexão automática. A escolha de separar Gateway e Engine reduz acoplamento e deixa o failover mais fácil de explicar e testar.

### Ordem sugerida para falar

1. Problema que o sistema resolve: chat multiusuário com tolerância a falhas.
2. Arquitetura geral: navegador → gateway → engine.
3. Protocolo: WebSocket na borda, TCP no núcleo.
4. Concorrência: uma thread por cliente no engine.
5. Falha e recuperação: heartbeat do backup e reconexão no gateway.
6. Demonstração: envio de mensagens e simulação de queda.

### Frases curtas úteis na apresentação

- “O Gateway traduz protocolos; o Engine concentra a lógica de chat.”
- “Cada cliente ganha uma thread própria, mas não um core fixo.”
- “O sistema não depende de um único ponto de falha porque há monitoramento e failover.”
- “HTTP aparece para healthcheck e para probes, mas o chat em si usa TCP e WebSocket.”