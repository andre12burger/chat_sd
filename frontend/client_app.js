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
    
    messageDiv.innerHTML = renderMessageText(message);
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
        document.getElementById('toolsSection').style.display = 'flex';
        status.textContent = `Conectado como: ${username}`;
        document.getElementById('messageInput').focus();
    } else {
        loginSection.style.display = 'flex';
        inputSection.style.display = 'none';
        document.getElementById('toolsSection').style.display = 'none';
        document.getElementById('gifPicker').style.display = 'none';
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

let emojiPicker;

function initEmojiPicker() {
    if (!window.EmojiButton) return;
    emojiPicker = new EmojiButton({ position: 'top-start' });
    emojiPicker.on('emoji', selection => {
        const input = document.getElementById('messageInput');
        input.value += selection.emoji;
        input.focus();
    });
}

function openEmojiPicker() {
    if (!emojiPicker) return;
    const button = document.getElementById('emojiPickerBtn');
    emojiPicker.togglePicker(button);
}

function renderMessageText(rawMessage) {
    const escaped = escapeHtml(rawMessage);
    const emojiText = replaceEmojiShortcodes(escaped);
    const markdownText = replaceMarkdown(emojiText);
    const mediaText = embedMedia(markdownText);
    const linkedText = linkify(mediaText);
    return linkedText;
}

function escapeHtml(text) {
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

const emojiMap = {
    smile: '😄',
    thumbsup: '👍',
    heart: '❤️',
    clap: '👏',
    wink: '😉',
    laugh: '😂',
    sad: '😢',
    angry: '😠',
    party: '🥳',
    fire: '🔥',
    star: '⭐',
};

function replaceEmojiShortcodes(text) {
    return text.replace(/:([a-z0-9_+-]+):/gi, (match, name) => {
        const key = name.toLowerCase();
        return emojiMap[key] || match;
    });
}

function replaceMarkdown(text) {
    if (window.marked) {
        return marked.parseInline(text, { breaks: true, mangle: false, headerIds: false });
    }
    // Fallback caso marked não esteja disponível
    text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/__(.+?)__/g, '<strong>$1</strong>');
    text = text.replace(/\*(.+?)\*/g, '<em>$1</em>');
    text = text.replace(/_(.+?)_/g, '<em>$1</em>');
    text = text.replace(/~~(.+?)~~/g, '<del>$1</del>');
    text = text.replace(/`(.+?)`/g, '<code>$1</code>');
    return text;
}

function linkify(text) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(text, 'text/html');
    const walker = doc.createTreeWalker(doc.body, NodeFilter.SHOW_TEXT, null, false);
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    const textNodes = [];

    while (walker.nextNode()) {
        textNodes.push(walker.currentNode);
    }

    textNodes.forEach(node => {
        const originalText = node.textContent;
        if (!originalText) return;

        const fragments = [];
        let lastIndex = 0;
        let match;

        while ((match = urlRegex.exec(originalText)) !== null) {
            const url = match[0];
            const before = originalText.slice(lastIndex, match.index);
            if (before) fragments.push(document.createTextNode(before));

            const anchor = doc.createElement('a');
            anchor.href = url;
            anchor.target = '_blank';
            anchor.rel = 'noreferrer';
            anchor.textContent = url;
            fragments.push(anchor);

            lastIndex = match.index + url.length;
        }

        if (fragments.length > 0) {
            const after = originalText.slice(lastIndex);
            if (after) fragments.push(document.createTextNode(after));
            fragments.forEach(fragment => node.parentNode.insertBefore(fragment, node));
            node.parentNode.removeChild(node);
        }
    });

    return doc.body.innerHTML;
}

function embedMedia(text) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(text, 'text/html');
    const anchors = Array.from(doc.querySelectorAll('a'));

    anchors.forEach(a => {
        const url = a.href || a.textContent;
        const lower = url.toLowerCase();
        if (lower.match(/\.(png|jpe?g|gif|webp)(\?|$)/)) {
            const img = doc.createElement('img');
            img.src = url;
            img.alt = 'imagem';
            a.parentNode.replaceChild(img, a);
        }
    });

    return doc.body.innerHTML;
}

function toggleGifPicker() {
    const picker = document.getElementById('gifPicker');
    const visible = picker.style.display === 'block';
    picker.style.display = visible ? 'none' : 'block';
    if (!visible) {
        document.getElementById('gifSearchInput').focus();
    }
}

async function searchGifs() {
    const query = document.getElementById('gifSearchInput').value.trim();
    if (!query) return;

    const apiKey = 'LIVDSRZULELA';
    const endpoint = `https://g.tenor.com/v1/search?q=${encodeURIComponent(query)}&key=${apiKey}&limit=12`;

    try {
        const response = await fetch(endpoint);
        const data = await response.json();
        const results = data.results || [];
        const container = document.getElementById('gifResults');
        container.innerHTML = '';

        results.forEach(item => {
            const media = item.media && item.media[0];
            const gifData = media && (media.gif || media.tinygif || media.mediumgif || media.nanogif);
            const gifUrl = gifData && gifData.url;
            if (!gifUrl) return;

            const thumb = document.createElement('div');
            thumb.className = 'gif-result';
            thumb.innerHTML = `<img src="${gifUrl}" alt="GIF" />`;
            thumb.addEventListener('click', () => {
                document.getElementById('messageInput').value = gifUrl;
                document.getElementById('messageInput').focus();
                toggleGifPicker();
            });
            container.appendChild(thumb);
        });
    } catch (error) {
        console.error('Erro ao buscar GIFs:', error);
    }
}

// ============================================================================
// ATALHOS DE TECLADO
// ============================================================================

/**
 * Enter no input de mensagem = enviar
 */
document.addEventListener('DOMContentLoaded', function() {
    initEmojiPicker();

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

    const gifSearchInput = document.getElementById('gifSearchInput');
    if (gifSearchInput) {
        gifSearchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                searchGifs();
            }
        });
    }
});
