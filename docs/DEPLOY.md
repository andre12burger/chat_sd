# Guia de Deploy - Render.com + UptimeRobot

## Estratégia: Projeto Online 24/7 (Gratuito)

Este guia explica como colocar seu Chat Distribuído online de forma **gratuita, confiável e sempre ativo** até a data da avaliação do professor.

---

## Problema: Plano Gratuito do Render

O Render.com oferece hospedagem **totalmente gratuita**, mas com uma limitação: servidores inativos por **15 minutos são colocados para "dormir"** (spin down). Quando o professor tentar acessar, o site demorará ~50 segundos para acordar.

**Solução:** UptimeRobot faz "pings" automáticos a cada 5 minutos, mantendo seu servidor sempre acordado.

---

## Passo 1: Preparar o GitHub

### 1.1 Inicializar Git (se ainda não fez)

```powershell
cd d:\Program_boy\Github\Chat_SD
git init
git add .
git commit -m "Projeto Chat Distribuído - Pronto para deploy"
```

### 1.2 Subir para GitHub

1. Crie um repositório **público** em https://github.com/new
2. Copie o comando de push que o GitHub fornece:
```powershell
git remote add origin https://github.com/SEU_USUARIO/Chat_SD.git
git branch -M main
git push -u origin main
```

**Resultado:** Seu código está online no GitHub ✓

---

## Passo 2: Criar Conta no Render.com

1. Acesse https://render.com
2. Clique em **"Sign Up"** (pode usar GitHub para facilitar)
3. Faça login

---

## Passo 3: Conectar GitHub ao Render

1. No dashboard do Render, clique em **"New +"**
2. Selecione **"Web Service"**
3. Clique em **"Connect a repository"**
4. Autorizee o Render a acessar seu GitHub
5. Selecione o repositório **Chat_SD**

---

## Passo 4: Configurar o Render

Preencha os campos assim:

| Campo | Valor |
|-------|-------|
| **Name** | `chat-distribuido` (sem espaços) |
| **Region** | Selecione a mais próxima (ex: São Paulo) |
| **Branch** | `main` |
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `bash start.sh` |
| **Plan** | Free |

---

## Passo 5: Deploy

1. Clique em **"Create Web Service"**
2. O Render vai:
   - ✅ Clonar seu repositório
   - ✅ Instalar `requirements.txt`
   - ✅ Executar `start.sh`
   - ✅ Gerar um URL (ex: `https://chat-distribuido.onrender.com`)

3. Aguarde até ver **"deployed"** em verde

**Resultado:** Seu chat está online! ✓

---

## Passo 6: Testar o Deploy

Abra em um navegador:
```
https://chat-distribuido.onrender.com
```

Se aparecer a interface do chat, **funcionou!** 🎉

---

## Passo 7: Mantê-lo Acordado com UptimeRobot (24/7)

### 7.1 Criar Conta no UptimeRobot

1. Acesse https://uptimerobot.com
2. Clique em **"Sign Up"** (versão gratuita)
3. Faça login

### 7.2 Criar Monitor

1. Clique em **"Add Monitor"**
2. Preencha assim:

| Campo | Valor |
|-------|-------|
| **Monitor Type** | HTTP(s) |
| **Friendly Name** | `Chat Distribuído - Test` |
| **URL** | `https://chat-distribuido.onrender.com` |
| **Monitoring Interval** | 5 minutes |

3. Clique em **"Create Monitor"**

**Resultado:** UptimeRobot agora "clica" no seu site a cada 5 minutos, impedindo que ele durma. ✓

---

## Passo 8: Usar o Projeto Online

Todos os usuários agora acessam:
```
https://chat-distribuido.onrender.com
```

E podem conversar em tempo real!

---

## Arquitetura na Nuvem

```
┌─ GitHub ──────────────────────────┐
│ Seu código versionado             │
└────────────┬──────────────────────┘
             │ (clone automático)
             ▼
┌─ Render.com ────────────────────────────────┐
│  Container com Python:                      │
│  ├─ chat_engine.py (porta 5000, localhost)  │
│  └─ web_gateway.py (porta pública)          │
│                                             │
│  URL: https://chat-distribuido.onrender.com│
└────────────┬────────────────────────────────┘
             │
             │ (acesso web)
             ▼
┌─ Browser do Professor ──────────┐
│ Testa o chat em tempo real      │
└─────────────────────────────────┘

┌─ UptimeRobot ──────────────────────────────┐
│ Faz ping a cada 5 minutos                  │
│ Mantém o Render acordado 24/7              │
└────────────────────────────────────────────┘
```

---

## Debugging: Logs no Render

Se algo der errado:

1. No dashboard do Render, clique no seu serviço
2. Vá para **"Logs"**
3. Procure por erros

### Logs Locais

Seu `start.sh` também salva logs:
```bash
cat logs_engine.txt  # Logs do Chat Engine
```

---

## Atualizar o Projeto (depois)

Se você fizer mudanças no código:

```powershell
git add .
git commit -m "Descrição da mudança"
git push origin main
```

O Render **automaticamente** detecta e faz deploy novamente! (pode levar 2-3 minutos)

---

## Checklist Pré-Avaliação (1 semana antes)

- [ ] Chat online em `https://seu-chat.onrender.com`
- [ ] UptimeRobot monitorando (mostra "up" em verde)
- [ ] 3+ abas do navegador conseguem conversar simultaneamente
- [ ] Logs do `chat_engine.py` mostram threads sendo criadas
- [ ] Documentação de Threads/Locks pronta para Overleaf

---

## Troubleshooting

### "Site toma muito tempo para carregar"
→ Render foi desligado. UptimeRobot não está monitorando corretamente. Verifique se o URL está correto no UptimeRobot.

### "Conexão recusada ao conectar ao chat_engine"
→ O `start.sh` não executou o `chat_engine.py`. Verifique os logs do Render.

### "Erro de porta"
→ Certifique-se de que `web_gateway.py` está usando `os.environ.get('PORT', 5001)` e não uma porta fixa.

### "Gateway não consegue conectar ao Engine"
→ Verifique se `chat_engine.py` está usando `127.0.0.1` (não `0.0.0.0`).

---

## Próximos Passos

Depois que o chat está online e funcionando:

1. **Testar a tolerância a falhas** com `backup_server.py`
2. **Documentar tudo no Overleaf** com screenshots dos logs
3. **Fazer um vídeo demonstrativo** mostrando múltiplos clientes conversando

---

**Data de atualização:** 17 de maio de 2026  
**Status:** Pronto para deploy em produção ✓
