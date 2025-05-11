// admin_frontend/admin_login.js

// API_PANEL_ENDPOINTS_BASE, etc., são definidos em admin_app_config.js

let fingerprintJsAgent = null;
let clientFingerprintValue = 'initializing-fp'; // Valor inicial indicando processo

function showMessageOnLogin(message, isError = false) {
    const loginMessageElement = document.getElementById('loginMessage');
    if (!loginMessageElement) return;
    loginMessageElement.textContent = message;
    loginMessageElement.className = 'message-area ' + (isError ? 'error-message' : 'success-message');
    loginMessageElement.style.display = message ? 'block' : 'none';
    
    if (message && !isError) {
        setTimeout(() => {
            if (loginMessageElement.textContent === message) {
                 loginMessageElement.style.display = 'none';
                 loginMessageElement.textContent = '';
            }
        }, MESSAGE_TIMEOUT_DURATION);
    }
}

async function initializeAndGetFingerprint() {
    const clientFingerprintInput = document.getElementById('clientFingerprint');
    if (typeof FingerprintJS === 'undefined') {
        console.error('FingerprintJS global não está definido. O script do CDN pode não ter carregado ou foi bloqueado.');
        clientFingerprintValue = 'fpjs-not-loaded';
        if (clientFingerprintInput) clientFingerprintInput.value = clientFingerprintValue;
        showMessageOnLogin('Falha crítica ao carregar componente de identificação. O login seguro não pode prosseguir.', true);
        const loginButton = document.getElementById('loginButton');
        if (loginButton) loginButton.disabled = true;
        return clientFingerprintValue;
    }

    try {
        logDebug('Tentando inicializar FingerprintJS Agent...');
        if (!fingerprintJsAgent) { // Inicializa apenas uma vez
             fingerprintJsAgent = await FingerprintJS.load(FP_JS_LOAD_OPTIONS);
        }
        logDebug('FingerprintJS Agent inicializado. Obtendo visitorId...');
        const result = await fingerprintJsAgent.get(FP_JS_GET_OPTIONS);
        clientFingerprintValue = result.visitorId;
        logDebug("FingerprintJS Visitor ID obtido:", clientFingerprintValue);
        if (clientFingerprintInput) clientFingerprintInput.value = clientFingerprintValue;
        return clientFingerprintValue;
    } catch (error) {
        console.error("Erro durante a inicialização ou obtenção do FingerprintJS:", error);
        showMessageOnLogin('Erro ao obter identificador do dispositivo. Tente recarregar.', true);
        clientFingerprintValue = 'fpjs-error-' + Date.now();
        if (clientFingerprintInput) clientFingerprintInput.value = clientFingerprintValue;
        return clientFingerprintValue;
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    const loginForm = document.getElementById('loginForm');
    const loginButton = document.getElementById('loginButton');
    const clientFingerprintInput = document.getElementById('clientFingerprint');

    // Habilitar o debug para esta sessão de teste
    // (Supondo que logDebug e FRONTEND_DEBUG_MODE estão em admin_app_config.js)
    // Se FRONTEND_DEBUG_MODE já estiver true, esta linha não é necessária.
    // FRONTEND_DEBUG_MODE = true; 
    
    logDebug("DOM carregado. Tentando inicializar Fingerprint.");
    // Tenta obter o fingerprint assim que o DOM estiver pronto.
    // O usuário pode tentar submeter o form antes disso, então também obtemos no submit.
    await initializeAndGetFingerprint(); 
    if (clientFingerprintValue.startsWith('fpjs-not-loaded') || clientFingerprintValue.startsWith('fpjs-error')) {
        // Se falhou aqui, o botão de login já pode estar desabilitado pela função.
        logDebug("Falha inicial na obtenção do fingerprint.");
    }


    if (loginForm && loginButton) {
        loginForm.addEventListener('submit', async function(event) {
            event.preventDefault();
            showMessageOnLogin('');
            loginButton.disabled = true;
            loginButton.textContent = 'Verificando...';

            const username = document.getElementById('username').value.trim();
            const password = document.getElementById('password').value;
            
            // Garante que tentamos obter o fingerprint mais atualizado no momento do submit,
            // especialmente se a primeira tentativa no DOMContentLoaded falhou ou demorou.
            let currentFingerprint = clientFingerprintInput.value;
            if (!currentFingerprint || currentFingerprint.startsWith('fpjs-') || currentFingerprint.startsWith('initializing-')) {
                logDebug("Fingerprint no input inválido ou não gerado, tentando obter novamente...");
                currentFingerprint = await initializeAndGetFingerprint();
            }
            
            if (!username || !password) {
                showMessageOnLogin('Usuário e senha são obrigatórios.', true);
                loginButton.disabled = false;
                loginButton.textContent = 'Entrar';
                return;
            }
            if (!currentFingerprint || currentFingerprint.startsWith('fpjs-') || currentFingerprint.startsWith('unavailable_') || currentFingerprint === 'initializing-fp') {
                showMessageOnLogin('Não foi possível obter um identificador de dispositivo válido. O login não pode prosseguir por razões de segurança. Tente recarregar a página.', true);
                loginButton.disabled = false;
                loginButton.textContent = 'Entrar';
                return;
            }

            logDebug('Enviando para login:', { username, client_hwid_identifier: currentFingerprint });

            try {
                const response = await fetch(`${API_PANEL_ENDPOINTS_BASE}/auth/token`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        username, 
                        password, 
                        client_hwid_identifier: currentFingerprint
                    }),
                });

                const data = await response.json();

                if (!response.ok) {
                    const errorDetail = data.detail || `Erro ${response.status}. Verifique suas credenciais ou o identificador do dispositivo.`;
                    showMessageOnLogin(errorDetail, true);
                    logDebug('Falha no login, resposta da API:', data);
                } else if (data.access_token) {
                    sessionStorage.setItem(TOKEN_STORAGE_KEY, data.access_token);
                    sessionStorage.setItem(TOKEN_TYPE_STORAGE_KEY, data.token_type || 'Bearer');
                    showMessageOnLogin('Login bem-sucedido! Redirecionando para o painel...', false);
                    setTimeout(() => { window.location.href = 'admin_dashboard.html'; }, REDIRECT_DELAY);
                } else {
                    showMessageOnLogin('Resposta inesperada do servidor. Token não recebido.', true);
                    logDebug('Resposta inesperada, sem token:', data);
                }
            } catch (error) {
                console.error('Erro na requisição de login:', error);
                showMessageOnLogin('Erro de comunicação com o servidor. Verifique sua conexão e tente novamente.', true);
            } finally {
                if (!window.location.href.endsWith('admin_dashboard.html')) {
                    loginButton.disabled = false;
                    loginButton.textContent = 'Entrar';
                }
            }
        });
    } else {
        if (!loginForm) console.error("Formulário de login não encontrado.");
        if (!loginButton) console.error("Botão de login não encontrado.");
    }
});
