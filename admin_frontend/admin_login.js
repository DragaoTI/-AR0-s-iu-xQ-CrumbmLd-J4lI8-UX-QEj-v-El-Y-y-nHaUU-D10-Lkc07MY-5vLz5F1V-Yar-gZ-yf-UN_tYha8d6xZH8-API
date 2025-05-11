// admin_frontend/admin_login.js

// API_BASE_URL, TOKEN_STORAGE_KEY, TOKEN_TYPE_STORAGE_KEY, FP_OPTIONS
// são definidos em admin_app_config.js e já devem estar carregados.

document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    const loginMessageElement = document.getElementById('loginMessage');
    const loginButton = document.getElementById('loginButton');
    const clientHwidIdentifierInput = document.getElementById('clientHwidIdentifier');

    function showMessage(message, isError = false) {
        if (!loginMessageElement) return;
        loginMessageElement.textContent = message;
        loginMessageElement.className = 'message-area ' + (isError ? 'error-message' : 'success-message');
        loginMessageElement.style.display = message ? 'block' : 'none';
    }

    async function getClientIdentifier() {
        if (typeof FingerprintJS === 'undefined') {
            console.warn('FingerprintJS não está carregado. Usando um identificador de fallback.');
            // Fallback muito simples (NÃO SEGURO PARA PRODUÇÃO COMO "HWID")
            return 'fallback|' + navigator.userAgent + '|' + (Math.random().toString(36) + Date.now().toString(36)).substring(2, 18);
        }
        try {
            // Inicializa o FingerprintJS com as opções de config
            const fpAgent = await FingerprintJS.load(FP_OPTIONS);
            const result = await fpAgent.get();
            // console.log("FingerprintJS Visitor ID:", result.visitorId);
            return result.visitorId; // Este é o identificador que será enviado
        } catch (error) {
            console.error("Erro ao obter o FingerprintJS Visitor ID:", error);
            showMessage('Erro ao obter identificador do dispositivo. O login pode não funcionar como esperado.', true);
            return 'error-generating-fp-' + (Math.random().toString(36) + Date.now().toString(36)).substring(2, 10);
        }
    }

    if (clientHwidIdentifierInput) {
        getClientIdentifier().then(identifier => {
            clientHwidIdentifierInput.value = identifier;
        }).catch(err => {
            console.error("Falha crítica ao obter identificador do cliente:", err);
            clientHwidIdentifierInput.value = "unavailable_hwid"; // Valor que indica falha
            showMessage("Não foi possível obter o identificador do dispositivo. Funcionalidade de HWID pode estar comprometida.", true);
        });
    } else {
        console.error("Elemento clientHwidIdentifier não encontrado no DOM.");
    }

    if (loginForm && loginButton) {
        loginForm.addEventListener('submit', async function(event) {
            event.preventDefault();
            showMessage(''); // Limpa mensagens anteriores
            loginButton.disabled = true;
            loginButton.textContent = 'Entrando...';

            const username = document.getElementById('username').value.trim();
            const password = document.getElementById('password').value; // Senhas não devem ter trim
            const client_hwid_identifier = clientHwidIdentifierInput.value;

            if (!username || !password) {
                showMessage('Usuário e senha são obrigatórios.', true);
                loginButton.disabled = false;
                loginButton.textContent = 'Entrar';
                return;
            }
            if (!client_hwid_identifier || client_hwid_identifier === "unavailable_hwid") {
                showMessage('Identificador do dispositivo não pôde ser obtido. Tente recarregar a página ou contate o suporte.', true);
                loginButton.disabled = false;
                loginButton.textContent = 'Entrar';
                return;
            }

            try {
                const response = await fetch(`${API_BASE_URL}/admin-panel/auth/token`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        // 'X-Requested-With': 'XMLHttpRequest' // Pode ajudar com algumas proteções CSRF
                    },
                    body: JSON.stringify({ username, password, client_hwid_identifier }),
                });

                const data = await response.json(); // Tenta parsear JSON mesmo em erro para pegar o `detail`

                if (!response.ok) {
                    // `data.detail` é o padrão do FastAPI para mensagens de erro em HTTPExceptions
                    showMessage(data.detail || `Erro ${response.status}: Falha no login. Verifique suas credenciais e o identificador do dispositivo.`, true);
                } else if (data.access_token) {
                    sessionStorage.setItem(TOKEN_STORAGE_KEY, data.access_token);
                    sessionStorage.setItem(TOKEN_TYPE_STORAGE_KEY, data.token_type || 'Bearer');
                    
                    showMessage('Login bem-sucedido! Redirecionando...', false);
                    // Adiciona um pequeno delay para o usuário ver a mensagem de sucesso
                    setTimeout(() => {
                        window.location.href = 'admin_dashboard.html';
                    }, 1000);
                } else {
                    showMessage('Resposta inesperada do servidor após o login.', true);
                }
            } catch (error) {
                console.error('Erro na requisição de login:', error);
                showMessage('Ocorreu um erro de rede ou o servidor está indisponível. Tente novamente mais tarde.', true);
            } finally {
                loginButton.disabled = false;
                loginButton.textContent = 'Entrar';
            }
        });
    } else {
        if (!loginForm) console.error("Formulário de login não encontrado.");
        if (!loginButton) console.error("Botão de login não encontrado.");
    }
});
