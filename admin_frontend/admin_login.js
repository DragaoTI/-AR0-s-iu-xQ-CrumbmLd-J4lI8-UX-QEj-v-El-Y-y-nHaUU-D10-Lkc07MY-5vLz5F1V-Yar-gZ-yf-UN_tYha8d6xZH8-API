// admin_frontend/admin_login.js

// Configurações globais (API_BASE_URL, etc.) são esperadas de admin_app_config.js

let fingerprintJsAgent = null;
let clientFingerprintValue = 'not-yet-generated'; // Valor inicial

// Chamado pelo onload do script FingerprintJS
function onFingerprintJsLoaded() {
    logDebug('FingerprintJS CDN script carregado com sucesso.');
    initializeFingerprintAgent();
}

// Chamado pelo onerror do script FingerprintJS
function onFingerprintJsError() {
    console.error('Falha ao carregar FingerprintJS CDN script.');
    showMessageOnLogin('Falha crítica ao carregar componente de identificação. O login seguro não pode prosseguir.', true);
    const loginButton = document.getElementById('loginButton');
    if (loginButton) loginButton.disabled = true; // Desabilita login se FPJS falhar
    clientFingerprintValue = 'fpjs-load-error';
    const clientFingerprintInput = document.getElementById('clientFingerprint');
    if (clientFingerprintInput) clientFingerprintInput.value = clientFingerprintValue;
}

async function initializeFingerprintAgent() {
    if (typeof FingerprintJS === 'undefined') {
        console.error('FingerprintJS global não está definido, mesmo após o evento onload.');
        onFingerprintJsError(); // Trata como erro de carregamento
        return;
    }
    try {
        fingerprintJsAgent = await FingerprintJS.load(FP_JS_LOAD_OPTIONS);
        logDebug('FingerprintJS Agent inicializado.');
        await updateClientFingerprintInput(); // Tenta preencher o input imediatamente
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
        await initializeFingerprintAgent(); // Tenta inicializar se ainda não estiver
        if (!fingerprintJsAgent) { // Se ainda falhar
            console.error('Não foi possível obter o fingerprint: Agent não inicializado.');
            return 'fpjs-agent-unavailable-' + Date.now(); // Fallback
        }
    }
    try {
        const result = await fingerprintJsAgent.get(FP_JS_GET_OPTIONS);
        logDebug("FingerprintJS Visitor ID:", result.visitorId);
        return result.visitorId;
    } catch (error) {
        console.error("Erro ao obter FingerprintJS Visitor ID:", error);
        return 'fpjs-get-error-' + Date.now(); // Fallback
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
    
    // Limpa a mensagem após um tempo se não for um erro crítico que impede o login
    if (message && !isError) { // Limpa apenas mensagens de sucesso ou informativas não críticas
        setTimeout(() => {
            if (loginMessageElement.textContent === message) { // Só limpa se for a mesma mensagem
                 loginMessageElement.style.display = 'none';
                 loginMessageElement.textContent = '';
            }
        }, MESSAGE_TIMEOUT_DURATION);
    }
}


document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    const loginButton = document.getElementById('loginButton');
    
    // O FingerprintJS começa a carregar devido ao 'async' no script tag.
    // onFingerprintJsLoaded() e initializeFingerprintAgent() serão chamados quando estiver pronto.
    // Se o script falhar, onFingerprintJsError() será chamado.

    if (loginForm && loginButton) {
        loginForm.addEventListener('submit', async function(event) {
            event.preventDefault();
            showMessageOnLogin(''); // Limpa mensagens anteriores
            loginButton.disabled = true;
            loginButton.textContent = 'Verificando...';

            const username = document.getElementById('username').value.trim();
            const password = document.getElementById('password').value;
            
            // Certifica-se de que temos o valor mais recente do fingerprint
            // Pode ser redundante se o updateClientFingerprintInput já rodou, mas garante
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
                const response = await fetch(`${API_BASE_URL}/admin-panel/auth/token`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        // 'Accept': 'application/json' // Boa prática
                    },
                    body: JSON.stringify({ 
                        username, 
                        password, 
                        client_hwid_identifier: currentFingerprint // Envia o fingerprint como client_hwid_identifier
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
                // Reabilita o botão apenas se não houver redirecionamento pendente
                if (window.location.href.endsWith('admin_login.html')) { // Checagem simples
                    loginButton.disabled = false;
                    loginButton.textContent = 'Entrar';
                }
            }
        });
    } else {
        console.error("Formulário de login ou botão não encontrado no DOM.");
    }
});
