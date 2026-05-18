/**
 * Chat Client Application
 * Lógica do cliente usando Socket.IO para comunicação com o Gateway
 */

const socket = io();
let connected = false;
let username = '';
let userStatus = 'online';
let statusMap = {};
let systemState = {
    serverRole: 'unknown',
    serverLabel: 'Indefinido',
    threadId: '—',
    threadName: 'Aguardando alocação',
    activeConnections: 0,
    cpuThreads: navigator.hardwareConcurrency || 1,
    serverHost: '127.0.0.1',
    serverPort: 5000,
};
let cpuPulseTimer = null;
let bannerTimer = null;
let nudgeSoundTimer = null;
let audioContext;

function ensureAudioContext() {
    if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
}

function playTone(frequency, duration = 0.1, type = 'sine') {
    try {
        ensureAudioContext();
        const osc = audioContext.createOscillator();
        const gain = audioContext.createGain();
        osc.type = type;
        osc.frequency.value = frequency;
        osc.connect(gain);
        gain.connect(audioContext.destination);
        gain.gain.setValueAtTime(0.15, audioContext.currentTime);
        osc.start();
        osc.stop(audioContext.currentTime + duration);
    } catch (error) {
        console.warn('Audio não disponível:', error);
    }
}

function playMessageSound() {
    playTone(880, 0.06, 'triangle');
    setTimeout(() => playTone(1320, 0.04, 'triangle'), 80);
}

function playNudgeSound() {
    playTone(520, 0.1, 'square');
    window.clearTimeout(nudgeSoundTimer);
    nudgeSoundTimer = window.setTimeout(() => playTone(620, 0.1, 'square'), 120);
}

function setTextContent(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
    }
}

function pulseCpuMeter() {
    const meter = document.getElementById('cpuMeterFill');
    if (!meter) return;

    meter.classList.remove('pulse');
    void meter.offsetWidth;
    meter.classList.add('pulse');

    window.clearTimeout(cpuPulseTimer);
    cpuPulseTimer = window.setTimeout(() => {
        meter.classList.remove('pulse');
    }, 350);
}

function setDashboardRoleBadge(role, label) {
    const badge = document.getElementById('serverRoleBadge');
    if (!badge) return;

    badge.classList.remove('primary', 'backup', 'alert');

    if (role === 'primary') {
        badge.classList.add('primary');
    } else if (role === 'backup') {
        badge.classList.add('backup');
    } else if (role === 'alert') {
        badge.classList.add('alert');
    }

    badge.textContent = label;
}

function showFailoverBanner(message, role) {
    const banner = document.getElementById('failoverBanner');
    const container = document.querySelector('.container');
    if (!banner || !container) return;

    banner.hidden = false;
    banner.textContent = message;
    container.classList.add('system-failover');

    window.clearTimeout(bannerTimer);
    bannerTimer = window.setTimeout(() => {
        banner.hidden = true;
        container.classList.remove('system-failover');
    }, role === 'backup' ? 7000 : 4500);
}

function renderConnectedUsers(users = []) {
    const tbody = document.getElementById('onlineUsersTable');
    if (!tbody) return;

    if (!users.length) {
        tbody.innerHTML = '<tr><td colspan="2" class="empty-state">Aguardando conexão</td></tr>';
        return;
    }

    tbody.innerHTML = users.map(user => {
        const threadLabel = user.thread_id ? `${user.thread_id}` : '—';
        return `
            <tr>
                <td>${escapeHtml(user.username || 'desconhecido')}</td>
                <td>${escapeHtml(threadLabel)}</td>
            </tr>
        `;
    }).join('');
}

function updateSystemDashboard(data = {}) {
    systemState = { ...systemState, ...data };

    const role = systemState.server_role || systemState.serverRole || 'unknown';
    const label =
        systemState.server_label ||
        systemState.serverLabel ||
        (role === 'primary' ? 'Primário' : role === 'backup' ? 'Backup' : 'Indefinido');
    systemState.serverRole = role;
    systemState.serverLabel = label;

    const threadId = systemState.thread_id ?? systemState.threadId ?? '—';
    const threadName = systemState.thread_name ?? systemState.threadName ?? 'Aguardando alocação';
    const activeConnections = systemState.active_web_clients ?? systemState.activeConnections ?? 0;
    const cpuThreads = systemState.cpu_threads ?? systemState.cpuThreads ?? (navigator.hardwareConcurrency || 1);
    const usernameLabel = systemState.username || username || 'Nenhum conectado';
    const connectedUsers = systemState.connected_users || [];

    setTextContent('dashboardServerRole', label);
    setTextContent('dashboardServerDetail', `${systemState.engine_host || '127.0.0.1'}:${systemState.engine_port || 5000} • ${systemState.state || 'standby'}`);
    setTextContent('dashboardUserName', usernameLabel);
    setTextContent('dashboardUserState', connected ? `Online • ${userStatus}` : 'Offline');
    setTextContent('dashboardThreadId', String(threadId));
    setTextContent('dashboardThreadName', threadName);
    setTextContent('dashboardConnections', String(activeConnections));
    setTextContent('dashboardCpu', `${cpuThreads} threads lógicos`);
    setTextContent('dashboardCpuHint', connected ? 'Processamento ativo' : 'Aguardando conexão');
    setTextContent('dashboardGatewayPid', String(systemState.gateway_pid || '—'));
    setTextContent('dashboardPrimaryState', label);
    setTextContent('dashboardBackupState', role === 'backup' ? 'Ativo' : 'Standby');
    setTextContent('dashboardSocketInfo', `${systemState.engine_host || '127.0.0.1'}:${systemState.engine_port || 5000}`);

    renderConnectedUsers(connectedUsers);

    setDashboardRoleBadge(role, label);

    if (role === 'backup') {
        const message = systemState.state === 'failover' || systemState.message
            ? systemState.message || '⚠ Servidor principal offline. Backup assumiu o controle.'
            : 'Backup em modo ativo.';
        showFailoverBanner(message, role);
    }
}

function setUserStatus(status) {
    const statusElement = document.getElementById('userStatus');
    if (!statusElement) return;
    userStatus = status;
    statusElement.textContent = status.charAt(0).toUpperCase() + status.slice(1);
    statusElement.classList.remove('online', 'away', 'busy', 'offline');
    statusElement.classList.add(status);
}

function handleStatusUpdate(sender, status) {
    statusMap[sender] = status;

    if (sender === username) {
        setUserStatus(status);
        updateSystemDashboard({ username: sender, user_status: status });
        displaySystemMessage(`Você agora está ${status}.`);
    } else {
        displaySystemMessage(`${sender} está agora ${status}.`);
    }
}

function triggerNudge(sender) {
    const chatWindow = document.querySelector('.container');
    if (chatWindow) {
        chatWindow.classList.add('nudge-shake');
        setTimeout(() => chatWindow.classList.remove('nudge-shake'), 500);
    }
    playNudgeSound();
    displaySystemMessage(`${sender} enviou um nudge!`);
}

function sendNudge() {
    const messageInput = document.getElementById('messageInput');
    socket.emit('send_message', { message: '/nudge' });
    if (messageInput) {
        messageInput.value = '';
        messageInput.focus();
    }
}

const emoticonMap = {
    ':)': '😀',
    ':(': '☹️',
    ':D': '😄',
    ';)': '😉',
    ':/': '😕',
    '(L)': '❤️',
    '(beer)': '🍺',
    '(party)': '🎉',
    '(heart)': '💖'
};

const winkMap = {
    porquinho: '🐷',
    beijo: '💋',
    foguete: '🚀',
    musica: '🎶',
    festa: '🎉'
};

function triggerWinkAnimation(name) {
    const container = document.querySelector('.container');
    if (!container) return;

    const icon = winkMap[name.toLowerCase()] || '✨';
    const overlay = document.createElement('div');
    overlay.className = 'wink-overlay';
    overlay.innerHTML = `
        <div class="wink-box">
            <div class="wink-icon">${icon}</div>
            <div class="wink-text">${name ? name.charAt(0).toUpperCase() + name.slice(1) : 'Wink'}!</div>
        </div>
    `;

    container.appendChild(overlay);
    playTone(520, 0.12, 'triangle');
    setTimeout(() => {
        overlay.classList.add('wink-hide');
    }, 2000);
    setTimeout(() => overlay.remove(), 2600);
}

function parseEmoticons(text) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(text, 'text/html');
    const walker = doc.createTreeWalker(doc.body, NodeFilter.SHOW_TEXT, null, false);
    const textNodes = [];

    while (walker.nextNode()) {
        textNodes.push(walker.currentNode);
    }

    textNodes.forEach(node => {
        const originalText = node.textContent;
        if (!originalText) return;

        let currentText = originalText;
        for (const shortcut of Object.keys(emoticonMap)) {
            const escaped = shortcut.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
            const regex = new RegExp(escaped, 'g');
            currentText = currentText.replace(regex, ` <span class="msn-emoticon">${emoticonMap[shortcut]}</span> `);
        }

        if (currentText !== originalText) {
            const wrapper = document.createElement('span');
            wrapper.innerHTML = currentText;
            node.parentNode.replaceChild(wrapper, node);
        }
    });

    return doc.body.innerHTML;
}

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
    pulseCpuMeter();
});

/**
 * Confirmação de conexão bem-sucedida ao chat
 */
socket.on('connection_success', function(data) {
    connected = true;
    username = data.username;
    setUserStatus('online');
    updateSystemDashboard({
        username: data.username,
        user_status: 'online',
        server_role: data.server_role,
        server_label: data.server_label,
        active_web_clients: data.active_web_clients,
    });
    updateUI();
    ensureAudioContext();
    displaySystemMessage(`Bem-vindo ao chat, ${username}!`);
});

socket.on('system_info', function(data) {
    updateSystemDashboard(data);
});

socket.on('system_state', function(data) {
    updateSystemDashboard(data);
});

socket.on('server_change', function(data) {
    updateSystemDashboard(data);
    const message = data.message || 'Servidor alterado.';
    showFailoverBanner(message, data.server_role);
    displaySystemMessage(message);
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
    userStatus = 'offline';
    setUserStatus('offline');
    updateSystemDashboard({ user_status: 'offline' });
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

    if (message.startsWith('/status ')) {
        const parts = message.split(' ');
        if (parts.length === 2) {
            const status = parts[1].toLowerCase();
            if (['online', 'away', 'busy', 'offline'].includes(status)) {
                socket.emit('send_message', { message: message });
                messageInput.value = '';
                messageInput.focus();
                return;
            }
        }
        displaySystemMessage('Use /status online, /status away, /status busy ou /status offline.');
        return;
    }

    socket.emit('send_message', { message: message });
    messageInput.value = '';
    messageInput.focus();
    pulseCpuMeter();
}

/**
 * Exibe uma mensagem na área de chat
 */
function displayMessage(message) {
    const chatArea = document.getElementById('chatArea');

    // Processa comandos especiais MSN-like
    if (/^[^:]+:\s*\/nudge$/i.test(message)) {
        const sender = message.split(':')[0];
        triggerNudge(sender);
        return;
    }

    const statusMatch = message.match(/^[^:]+:\s*\/status\s+(online|away|busy|offline)$/i);
    if (statusMatch) {
        const sender = message.split(':')[0];
        const status = statusMatch[1].toLowerCase();
        handleStatusUpdate(sender, status);
        return;
    }

    const winkMatch = message.match(/^[^:]+:\s*\/wink\s*([^\s]*)/i);
    if (winkMatch) {
        const sender = message.split(':')[0];
        const winkName = winkMatch[1] || 'wink';
        triggerWinkAnimation(winkName);
        displaySystemMessage(`${sender} enviou um wink ${winkName}!`);
        return;
    }

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

    if (!message.startsWith(username + ':')) {
        playMessageSound();
    }

    pulseCpuMeter();
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
    playTone(720, 0.04, 'triangle');
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
        status.textContent = `Conectado como: ${username} • ${userStatus} • ${systemState.serverLabel || 'Indefinido'}`;
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
    userStatus = 'offline';
    setUserStatus('offline');
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
    const emoticonText = parseEmoticons(markdownText);
    const mediaText = embedMedia(emoticonText);
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
    updateSystemDashboard({
        cpu_threads: navigator.hardwareConcurrency || 1,
        server_label: 'Indefinido',
    });

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
