// admin_frontend/admin_dashboard.js

// Configurações globais são esperadas de admin_app_config.js

document.addEventListener('DOMContentLoaded', () => {
    const token = sessionStorage.getItem(TOKEN_STORAGE_KEY);
    const tokenType = sessionStorage.getItem(TOKEN_TYPE_STORAGE_KEY) || 'Bearer';

    const mainDashboardContentElement = document.getElementById('mainDashboardContent');
    const loggedInUserElement = document.getElementById('loggedInUser');
    const logoutButton = document.getElementById('logoutButton');
    const dashboardMessageElement = document.getElementById('dashboardMessage');
    const navButtons = document.querySelectorAll('.dashboard-nav button');

    function showDashboardMessage(message, isError = false, autoClear = true) {
        if (!dashboardMessageElement) return;
        logDebug(`Dashboard Message (${isError ? 'Error' : 'Success'}): ${message}`);
        dashboardMessageElement.textContent = message;
        dashboardMessageElement.className = 'message-area ' + (isError ? 'error-message' : 'success-message');
        dashboardMessageElement.style.display = message ? 'block' : 'none';
        
        if (message && autoClear) {
            setTimeout(() => {
                if (dashboardMessageElement.textContent === message) {
                    dashboardMessageElement.style.display = 'none';
                    dashboardMessageElement.textContent = '';
                }
            }, MESSAGE_TIMEOUT_DURATION);
        }
    }

    if (!token) {
        logDebug("Nenhum token encontrado, redirecionando para login.");
        window.location.href = 'admin_login.html';
        return;
    }

    async function fetchApi(endpoint, method = 'GET', body = null) {
        const headers = {
            'Authorization': `${tokenType} ${token}`,
            'Content-Type': 'application/json',
            // 'Accept': 'application/json', // Boa prática
        };
        const config = { method, headers };
        if (body) {
            config.body = JSON.stringify(body);
        }

        logDebug(`API Call: ${method} ${endpoint}`, body || '');

        try {
            const response = await fetch(`${API_BASE_URL}${endpoint}`, config);

            if (response.status === 401) { // Não autorizado / token expirado
                logDebug("API retornou 401 - Token inválido/expirado.");
                sessionStorage.removeItem(TOKEN_STORAGE_KEY);
                sessionStorage.removeItem(TOKEN_TYPE_STORAGE_KEY);
                showDashboardMessage('Sessão inválida ou expirada. Por favor, faça login novamente.', true, false);
                setTimeout(() => window.location.href = 'admin_login.html', REDIRECT_DELAY + 1000);
                return null;
            }
            
            // Para DELETE ou respostas 204 No Content, não haverá corpo JSON
            if (response.status === 204) {
                logDebug(`API Call Success (204 No Content): ${method} ${endpoint}`);
                return { success: true, status: 204 };
            }

            const data = await response.json(); // Tenta parsear JSON
            logDebug(`API Response (${response.status}): ${method} ${endpoint}`, data);


            if (!response.ok) {
                // data.detail é o padrão do FastAPI para mensagens de erro em HTTPExceptions
                throw new Error(data.detail || `Erro HTTP ${response.status}`);
            }
            return data;
        } catch (error) {
            console.error(`Erro na chamada API para ${endpoint} (${method}):`, error);
            showDashboardMessage(`Erro na API: ${error.message || 'Falha na comunicação.'}`, true);
            return null;
        }
    }

    async function loadCurrentAdminInfo() {
        const adminData = await fetchApi('/admin-panel/me');
        if (adminData && loggedInUserElement) {
            loggedInUserElement.textContent = `Admin: ${adminData.username}`;
            // Após carregar info do admin, podemos carregar uma seção padrão
            navigateToSection('manageAdmins'); // Ou 'overview' se existir
        } else if (mainDashboardContentElement && !adminData) { // Se fetchApi retornou null devido a erro
            mainDashboardContentElement.innerHTML = "<p>Não foi possível carregar informações do administrador. A sessão pode ter expirado.</p>";
        }
    }

    function renderManageAdminsSection(admins) {
        let html = '<h3>Gerenciar Administradores</h3>';
        html += '<div class="admin-list">';
        if (admins && Array.isArray(admins)) {
            if (admins.length === 0) {
                html += '<p>Nenhum administrador encontrado.</p>';
            } else {
                html += '<ul>';
                admins.forEach(admin => {
                    const lastLogin = admin.last_login_at ? new Date(admin.last_login_at).toLocaleString('pt-BR') : 'Nunca';
                    html += `
                        <li>
                            <div class="admin-info">
                                <strong>${admin.username}</strong> (ID: ${admin.id.substring(0,8)}...)<br>
                                Status: ${admin.status} | Último Login: ${lastLogin}
                            </div>
                            <div class="actions">
                                <button class="button edit-admin" data-id="${admin.id}">Editar</button>
                                <!-- <button class="button delete-admin" data-id="${admin.id}">Excluir</button> -->
                            </div>
                        </li>`;
                });
                html += '</ul>';
            }
        } else {
            html += '<p>Erro ao carregar lista de administradores ou nenhum encontrado.</p>';
        }
        html += '</div>'; // Fim de .admin-list

        html += `
            <div class="form-section" id="adminFormContainer">
                <!-- O formulário de criar/editar será inserido aqui -->
            </div>
        `;
        if (mainDashboardContentElement) mainDashboardContentElement.innerHTML = html;
        renderAdminForm('create'); // Renderiza o formulário de criação por padrão
    }
    
    function renderAdminForm(mode = 'create', adminData = {}) {
        const formContainer = document.getElementById('adminFormContainer');
        if (!formContainer) return;

        const isEditMode = mode === 'edit';
        const title = isEditMode ? `Editar Administrador: ${adminData.username}` : 'Criar Novo Administrador';
        const submitButtonText = isEditMode ? 'Salvar Alterações' : 'Criar Administrador';
        const hwidNote = isEditMode ? 
            (adminData.has_hwid ? "HWID já registrado (digite novo para alterar/limpar)" : "Nenhum HWID registrado (digite para adicionar)")
            : "Identificador do Cliente (Fingerprint - opcional no cadastro)";

        let formHtml = `<h4>${title}</h4>`;
        formHtml += `<form id="adminUpsertForm" data-mode="${mode}" data-id="${isEditMode ? adminData.id : ''}" novalidate>`;
        
        formHtml += `<div class="form-group">
                        <label for="adminUsername">Username:</label>
                        <input type="text" id="adminUsername" value="${isEditMode ? adminData.username : ''}" placeholder="Pelo menos 3 caracteres" required>
                     </div>`;
        formHtml += `<div class="form-group">
                        <label for="adminPassword">${isEditMode ? 'Nova Senha (deixe em branco para não alterar)' : 'Senha:'}</label>
                        <input type="password" id="adminPassword" placeholder="Pelo menos 8 caracteres" ${!isEditMode ? 'required' : ''}>
                     </div>`;
        if (isEditMode) { // Campo de status apenas na edição
            formHtml += `<div class="form-group">
                            <label for="adminStatus">Status:</label>
                            <select id="adminStatus">
                                <option value="active" ${adminData.status === 'active' ? 'selected' : ''}>Ativo</option>
                                <option value="inactive" ${adminData.status === 'inactive' ? 'selected' : ''}>Inativo</option>
                            </select>
                         </div>`;
        }
        formHtml += `<div class="form-group">
                        <label for="adminClientFingerprint">${hwidNote}:</label>
                        <input type="text" id="adminClientFingerprint" placeholder="Será gerado/enviado se deixado em branco no login">
                        <small>No modo de edição, preencher este campo substituirá o identificador existente. Deixar em branco manterá o atual. Para limpar um HWID existente, digite a palavra "CLEAR_HWID".</small>
                     </div>`;
        formHtml += `<button type="submit" id="adminUpsertButton">${submitButtonText}</button>`;
        if (isEditMode) {
            formHtml += `<button type="button" id="cancelEditAdminButton" class="button" style="margin-left: 10px; background-color: #7f8c8d;">Cancelar Edição</button>`;
        }
        formHtml += `</form>`;
        
        formContainer.innerHTML = formHtml;
        
        const adminUpsertForm = document.getElementById('adminUpsertForm');
        if (adminUpsertForm) {
            adminUpsertForm.addEventListener('submit', handleAdminUpsertSubmit);
        }
        if (isEditMode) {
            const cancelButton = document.getElementById('cancelEditAdminButton');
            if (cancelButton) {
                cancelButton.addEventListener('click', () => renderAdminForm('create')); // Volta para o form de criação
            }
        }
    }

    async function handleAdminUpsertSubmit(event) {
        event.preventDefault();
        const form = event.target;
        const mode = form.dataset.mode;
        const adminId = form.dataset.id;
        const upsertButton = document.getElementById('adminUpsertButton');
        if (upsertButton) upsertButton.disabled = true;

        const username = document.getElementById('adminUsername').value.trim();
        const password = document.getElementById('adminPassword').value; // Não fazer trim
        const client_fingerprint_input = document.getElementById('adminClientFingerprint').value.trim();
        
        const payload = { username };
        if (password) { // Envia senha apenas se preenchida
            payload.password = password;
        }
        // Lógica para HWID/Fingerprint:
        // Se "CLEAR_HWID", envia null para o backend interpretar como limpar.
        // Se preenchido, envia o valor.
        // Se em branco no modo de edição, NÃO envia o campo (para não sobrescrever com vazio).
        // Se em branco no modo de criação, envia null (ou o backend pode tratar).
        if (client_fingerprint_input.toUpperCase() === "CLEAR_HWID") {
            payload.client_hwid_identifier = null; 
        } else if (client_fingerprint_input) {
            payload.client_hwid_identifier = client_fingerprint_input;
        } else if (mode === 'create') { // Para criação, se em branco, pode ser null ou o backend gera/ignora
            payload.client_hwid_identifier = null;
        }
        // Não enviamos client_hwid_identifier se estiver em branco no modo de edição para não sobrescrever acidentalmente


        let endpoint = '/admin-panel/administrators';
        let method = 'POST';

        if (mode === 'edit') {
            endpoint += `/${adminId}`;
            method = 'PUT';
            // Adicionar status ao payload para edição
            const statusValue = document.getElementById('adminStatus').value;
            payload.status = statusValue;
        }

        const result = await fetchApi(endpoint, method, payload);

        if (result && (result.id || result.success)) {
            showDashboardMessage(`Administrador ${mode === 'edit' ? 'atualizado' : 'criado'} com sucesso!`, false);
            navigateToSection('manageAdmins'); // Recarrega a seção
        } else {
            // Mensagem de erro já deve ter sido mostrada por fetchApi
        }
        if (upsertButton) upsertButton.disabled = false;
    }
    
    async function navigateToSection(sectionName) {
        logDebug("Navegando para a seção:", sectionName);
        if (!mainDashboardContentElement) return;
        mainDashboardContentElement.innerHTML = `<p>Carregando seção ${sectionName}...</p>`; // Feedback

        if (sectionName === 'manageAdmins') {
            const admins = await fetchApi('/admin-panel/administrators');
            renderManageAdminsSection(admins);
        } else if (sectionName === 'logs') {
            // mainDashboardContentElement.innerHTML = '<h3>Logs do Sistema</h3><p>Funcionalidade de logs a ser implementada.</p>';
            showDashboardMessage("Seção de Logs ainda não implementada.", false);
             mainDashboardContentElement.innerHTML = '<h3>Logs do Sistema</h3><p>Funcionalidade de logs a ser implementada.</p>';

        } else { // overview ou default
            mainDashboardContentElement.innerHTML = '<h3>Visão Geral</h3><p>Bem-vindo ao painel de administração. Selecione uma opção no menu para começar.</p>';
        }
    }
    
    function handleDashboardMainActions(event) {
        const target = event.target;
        if (target.classList.contains('edit-admin')) {
            event.preventDefault();
            const adminId = target.dataset.id;
            // Precisamos buscar os dados completos do admin para preencher o form de edição,
            // pois o dataset pode não ter tudo (ex: o HWID real não está ali, apenas o hash que não mostramos).
            // Ou, passamos os dados conhecidos e o backend lida com o resto.
            // Para este exemplo, vamos buscar os dados novamente.
            fetchApi(`/admin-panel/administrators/${adminId}`) // Assumindo que você criará este endpoint
                .then(adminData => {
                    if(adminData) {
                        renderAdminForm('edit', {
                            id: adminData.id,
                            username: adminData.username,
                            status: adminData.status,
                            // Importante: Não exponha o hash do HWID.
                            // O usuário digita um NOVO HWID se quiser mudar, ou deixa em branco.
                            // O backend que faz o hash do novo valor.
                            // Se quiser indicar que existe um, use um placeholder.
                            has_hwid: !!adminData.client_hwid_identifier_hash // Verdadeiro se o hash existir
                        });
                    }
                });
        }
        // Adicionar handler para deletar admin aqui, com confirmação!
        // if (target.classList.contains('delete-admin')) { ... }
    }

    if (mainDashboardContentElement) {
        mainDashboardContentElement.addEventListener('click', handleDashboardMainActions);
    }
    
    if (navButtons) {
        navButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const section = e.target.dataset.section;
                if (section) navigateToSection(section);
            });
        });
    }

    if (logoutButton) {
        logoutButton.addEventListener('click', async () => {
            showDashboardMessage('Saindo do sistema...', false, 10000);
            // Opcional: Chamar endpoint de logout da API se ele fizer algo útil
            // (ex: invalidar refresh tokens do lado do servidor, se implementado)
            // await fetchApi('/admin-panel/auth/logout', 'POST');

            sessionStorage.removeItem(TOKEN_STORAGE_KEY);
            sessionStorage.removeItem(TOKEN_TYPE_STORAGE_KEY);
            
            setTimeout(() => {
                window.location.href = 'admin_login.html';
            }, REDIRECT_DELAY / 2); // Um pouco mais rápido para logout
        });
    }

    // Carregar informações iniciais do admin e a seção padrão
    if (token) {
        loadCurrentAdminInfo();
    } else {
        // Isso não deveria acontecer se o primeiro check de token redirecionou.
        logDebug("Token não encontrado no carregamento do dashboard, redirecionando.");
        window.location.href = 'admin_login.html';
    }
});
