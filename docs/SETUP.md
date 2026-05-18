# Setup do Ambiente - Chat Distribuído

## 🎯 Status Atual

✅ Ambiente Conda criado: `chat_sd` (Python 3.10)  
✅ Todas as dependências instaladas  
✅ Pronto para desenvolvimento e testes

---

## 📋 Pré-requisitos

Você precisa ter instalado:
- **Conda/Miniconda** (já verificado ✓)
- **Python 3.10+** (já instalado no ambiente ✓)

---

## 🚀 Como Usar

### Opção 1: Ativar com PowerShell Script (Mais Fácil)

```powershell
cd d:\Program_boy\Github\Chat_SD
.\activate_env.ps1
```

Isso automaticamente ativa o ambiente.

### Opção 2: Ativar Manualmente

```powershell
conda activate chat_sd
```

---

## ✅ Verificar Instalação

Depois de ativar o ambiente, confirme que tudo está instalado:

```powershell
pip list
```

Você deve ver:
- ✓ Flask==2.3.3
- ✓ Flask-SocketIO==5.3.4
- ✓ python-socketio==5.9.0
- ✓ python-engineio==4.7.1
- ✓ eventlet==0.33.3
- ✓ python-dotenv==1.0.0

---

## 🧪 Teste Local (Dois Terminais)

### Terminal 1: Chat Engine

```powershell
conda activate chat_sd
python backend/chat_engine.py
```

Esperado:
```
2026-05-17 14:22:10,123 - [MainThread] - Chat Engine iniciado em 127.0.0.1:5000
```

### Terminal 2: Web Gateway

```powershell
conda activate chat_sd
python backend/web_gateway.py
```

Esperado:
```
 * Running on http://0.0.0.0:5001
```

### Navegador: 3+ Abas

Abra `http://localhost:5001` em 3 abas diferentes com usernames:
- alice
- bob
- charlie

Envie mensagens cruzadas. Verifique se tudo aparece sincronizado.

---

## 📊 Verificar Threads nos Logs

No Terminal 1 (Chat Engine), procure por:

```
ClientThread-54321 iniciada. Total de threads ativas: 3
Cliente registrado: alice. Total: 1
Mensagem de alice: Olá!
```

Isso prova que:
✓ Threads estão sendo criadas explicitamente  
✓ Locks estão funcionando corretamente  
✓ Broadcast está sincronizado

---

## 🛠️ Troubleshooting

### "Conda não é reconhecido"
Reinstale Miniconda/Anaconda e reinicie o PowerShell.

### "Módulo não encontrado: flask"
```powershell
conda activate chat_sd
pip install -r requirements.txt
```

### "Porta 5000/5001 já em uso"
```powershell
# Encontre o processo:
netstat -ano | findstr :5001

# Encerre-o:
taskkill /PID <PID> /F
```

### "ImportError no web_gateway.py"
Verifique que os arquivos estão na pasta `frontend/`:
```powershell
ls frontend/
```

Deve listar:
- index.html
- style.css
- client_app.js

---

## 📦 Gerenciar o Ambiente

### Listar todos os ambientes conda

```powershell
conda env list
```

### Remover o ambiente (se necessário)

```powershell
conda remove -n chat_sd --all
```

### Criar novamente

```powershell
conda create -n chat_sd python=3.10 -y
conda activate chat_sd
pip install -r requirements.txt
```

---

## 🎓 Para o Relatório Overleaf

Capture prints dos logs quando estiver rodando com 3 clientes:

1. **Screenshot do Terminal 1** mostrando:
   - Threads sendo criadas: `ClientThread-...`
   - Clientes registrados: `Cliente registrado: alice`
   - Broadcast: `Mensagem de alice: ...`

2. **Screenshot do Browser** mostrando:
   - 3 abas conversando simultaneamente
   - Mensagens sincronizadas

Esses prints são ouro puro para demonstrar a concorrência funcionando.

---

## ✨ Próximos Passos

Depois de confirmar que tudo funciona localmente:

1. `git init` + `git push` para GitHub
2. Deploy no Render.com (siga DEPLOY.md)
3. Monitoramento com UptimeRobot
4. Documentação no Overleaf

---

**Data de Criação:** 17 de maio de 2026  
**Status:** Ambiente pronto para desenvolvimento ✓
