/**
 * Chat Client Application
 * Lógica do cliente usando Socket.IO para comunicação com o Gateway
 */

const socket = io();
let connected = false;
let username = '';

// ============================================================================
// EVENTOS SOCKETIO
// ============================================================================

/**
 * Conectado ao servidor Web Gateway
 */
socket.on('connect', function() {
    console.log('✓ Conectado ao servidor Web Gateway');
});

/**
 * Recebe mensagem do servidor (vindo do chat_engine)
 */
socket.on('receive_message', function(data) {
    displayMessage(data.message);
});

/**
 * Confirmação de conexão bem-sucedida ao chat
 */
socket.on('connection_success', function(data) {
    connected = true;
    username = data.username;
    updateUI();
    displaySystemMessage(`Bem-vindo ao chat, ${username}!`);
});

/**
 * Erro ao tentar conectar
 */
socket.on('connection_error', function(data) {
    alert('Erro: ' + data.error);
    resetUI();
});

/**
 * Desconectado do servidor
 */
socket.on('disconnect', function() {
    console.log('✗ Desconectado do servidor');
    connected = false;
    updateUI();
});

// ============================================================================
// FUNÇÕES DE INTERFACE
// ============================================================================

/**
 * Conecta o usuário ao chat
 * Chamado quando clica no botão "Conectar"
 */
function connect() {
    const usernameInput = document.getElementById('usernameInput').value.trim();
    
    if (!usernameInput) {
        alert('Digite um username!');
        return;
    }
    
    document.getElementById('connectBtn').disabled = true;
    document.getElementById('usernameInput').disabled = true;
    
    // Emite evento para o servidor
    socket.emit('join_chat', { username: usernameInput });
}

/**
 * Envia uma mensagem para o chat
 * Chamado quando clica no botão "Enviar" ou pressiona Enter
 */
function sendMessage() {
    const messageInput = document.getElementById('messageInput');
    const message = messageInput.value.trim();
    
    if (!message) return;
    
    // Emite evento para o servidor
    socket.emit('send_message', { message: message });
    messageInput.value = '';
    messageInput.focus();
}

/**
 * Exibe uma mensagem na área de chat
 */
function displayMessage(message) {
    const chatArea = document.getElementById('chatArea');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';
    
    // Classifica o tipo de mensagem
    if (message.includes('[SYSTEM]')) {
        messageDiv.className = 'message system';
    } else if (message.startsWith(username + ':')) {
        messageDiv.className = 'message own';
    } else {
        messageDiv.className = 'message other';
    }
    
    messageDiv.textContent = message;
    chatArea.appendChild(messageDiv);
    chatArea.scrollTop = chatArea.scrollHeight;
}

/**
 * Exibe uma mensagem de sistema
 */
function displaySystemMessage(message) {
    const chatArea = document.getElementById('chatArea');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message system';
    messageDiv.textContent = '[SYSTEM] ' + message;
    chatArea.appendChild(messageDiv);
    chatArea.scrollTop = chatArea.scrollHeight;
}

/**
 * Atualiza a interface de acordo com o estado de conexão
 */
function updateUI() {
    const loginSection = document.getElementById('loginSection');
    const inputSection = document.getElementById('inputSection');
    const status = document.getElementById('status');
    
    if (connected) {
        loginSection.style.display = 'none';
        inputSection.style.display = 'flex';
        status.textContent = `Conectado como: ${username}`;
        document.getElementById('messageInput').focus();
    } else {
        loginSection.style.display = 'flex';
        inputSection.style.display = 'none';
        status.textContent = 'Desconectado';
        document.getElementById('usernameInput').focus();
    }
}

/**
 * Reseta a interface para o estado inicial
 */
function resetUI() {
    document.getElementById('connectBtn').disabled = false;
    document.getElementById('usernameInput').disabled = false;
    document.getElementById('usernameInput').value = '';
    updateUI();
}

// ============================================================================
// ATALHOS DE TECLADO
// ============================================================================

/**
 * Enter no input de mensagem = enviar
 */
document.addEventListener('DOMContentLoaded', function() {
    const messageInput = document.getElementById('messageInput');
    const usernameInput = document.getElementById('usernameInput');
    
    if (messageInput) {
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    }
    
    if (usernameInput) {
        usernameInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                connect();
            }
        });
    }
});
