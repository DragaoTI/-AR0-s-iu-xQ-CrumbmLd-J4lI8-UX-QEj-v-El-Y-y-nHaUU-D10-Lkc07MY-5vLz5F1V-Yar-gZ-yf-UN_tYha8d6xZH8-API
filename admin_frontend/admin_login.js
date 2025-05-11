// admin_frontend/admin_login.js

// API_PANEL_ENDPOINTS_BASE, TOKEN_STORAGE_KEY, etc., são definidos em admin_app_config.js

let fingerprintJsAgent = null;
let clientFingerprintValue = 'not-yet-generated';

function onFingerprintJsLoaded() {
    logDebug('FingerprintJS CDN script carregado com sucesso.');
    initializeFingerprintAgent();
}

function onFingerprintJsError() {
    console.error('Falha ao carregar FingerprintJS CDN script.');
    showMessageOnLogin('Falha crítica ao carregar componente de identificação. O login seguro não pode prosseguir.', true);
    const loginButton = document.getElementById('loginButton');
    if (loginButton) loginButton.disabled = true;
    clientFingerprintValue = 'fpjs-load-error';
    const clientFingerprintInput = document.getElementById('clientFingerprint');
    if (clientFingerprintInput) clientFingerprintInput.value = clientFingerprintValue;
}

async function initializeFingerprintAgent() {
    if (typeof FingerprintJS === 'undefined') {
        console.error('FingerprintJS global não está definido, mesmo após o evento onload.');
        onFingerprintJsError();
        return;
    }
    try {
        fingerprintJsAgent = await FingerprintJS.load(FP_JS_LOAD_OPTIONS);
        logDebug('FingerprintJS Agent inicializado.');
        await updateClientFingerprintInput();
    } catch (error) {
        console.error("Erro ao inicializar FingerprintJS Agent:", error);
        showMessageOnLogin('Erro ao inicializar componente de identificação.', true);
        clientFingerprintValue = 'fpjs-init-error';
        const clientFingerprintInput = document.getElementById('clientFingerprint');
        if (clientFingerprintInput) clientFingerprintInput.value = clientFingerprintValue;
    }
}

async function getClientFingerprint() {
    if (!fingerprintJsAgent) {
        logDebug('FingerprintJS Agent não está pronto, tentando inicializar...');
        await initializeFingerprintAgent();
        if (!fingerprintJsAgent) {
            console.error('Não foi possível obter o fingerprint: Agent não inicializado.');
            return 'fpjs-agent-unavailable-' + Date.now();
        }
    }
    try {
        const result = await fingerprintJsAgent.get(FP_JS_GET_OPTIONS);
        logDebug("FingerprintJS Visitor ID:", result.visitorId);
        return result.visitorId;
    } catch (error) {
        console.error("Erro ao obter FingerprintJS Visitor ID:", error);
        return 'fpjs-get-error-' + Date.now();
    }
}

async function updateClientFingerprintInput() {
    const clientFingerprintInput = document.getElementById('clientFingerprint');
    if (clientFingerprintInput) {
        clientFingerprintValue = await getClientFingerprint();
        clientFingerprintInput.value = clientFingerprintValue;
        logDebug('Input clientFingerprint atualizado com:', clientFingerprintValue);
    } else {
        console.error("Elemento clientFingerprint não encontrado no DOM para atualização.");
    }
}

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

document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    const loginButton = document.getElementById('loginButton');
    
    if (loginForm && loginButton) {
        loginForm.addEventListener('submit', async function(event) {
            event.preventDefault();
            showMessageOnLogin('');
            loginButton.disabled = true;
            loginButton.textContent = 'Verificando...';

            const username = document.getElementById('username').value.trim();
            const password = document.getElementById('password').value;
            
            const currentFingerprint = await getClientFingerprint();
            const clientFingerprintInput = document.getElementById('clientFingerprint');
            if (clientFingerprintInput) clientFingerprintInput.value = currentFingerprint;

            if (!username || !password) {
                showMessageOnLogin('Usuário e senha são obrigatórios.', true);
                loginButton.disabled = false;
                loginButton.textContent = 'Entrar';
                return;
            }
            if (!currentFingerprint || currentFingerprint.startsWith('fpjs-') || currentFingerprint.startsWith('unavailable_')) {
                showMessageOnLogin('Não foi possível obter um identificador de dispositivo válido. O login não pode prosseguir por razões de segurança.', true);
                loginButton.disabled = false;
                loginButton.textContent = 'Entrar';
                return;
            }

            logDebug('Enviando para login:', { username, client_fingerprint: currentFingerprint });

            try {
                // USA A NOVA CONSTANTE API_PANEL_ENDPOINTS_BASE
                const response = await fetch(`${API_PANEL_ENDPOINTS_BASE}/auth/token`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
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
                    setTimeout(() => {
                        window.location.href = 'admin_dashboard.html';
                    }, REDIRECT_DELAY);
                } else {
                    showMessageOnLogin('Resposta inesperada do servidor. Token não recebido.', true);
                    logDebug('Resposta inesperada, sem token:', data);
                }
            } catch (error) {
                console.error('Erro na requisição de login:', error);
                showMessageOnLogin('Erro de comunicação com o servidor. Verifique sua conexão e tente novamente.', true);
            } finally {
                if (window.location.href.endsWith('admin_login.html')) {
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
