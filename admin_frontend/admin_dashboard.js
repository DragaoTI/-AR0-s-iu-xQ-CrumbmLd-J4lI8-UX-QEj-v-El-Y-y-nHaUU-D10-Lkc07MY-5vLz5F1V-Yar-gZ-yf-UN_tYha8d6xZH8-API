// admin_frontend/admin_dashboard.js

// API_PANEL_ENDPOINTS_BASE, TOKEN_STORAGE_KEY, etc., são definidos em admin_app_config.js

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

    async function fetchApi(shortEndpoint, method = 'GET', body = null) {
        const headers = {
            'Authorization': `${tokenType} ${token}`,
            'Content-Type': 'application/json',
        };
        const config = { method, headers };
        if (body) {
            config.body = JSON.stringify(body);
        }

        const fullUrl = `${API_PANEL_ENDPOINTS_BASE}${shortEndpoint}`;
        logDebug(`API Call: ${method} ${fullUrl}`, body || '');

        try {
            const response = await fetch(fullUrl, config);
            if (response.status === 401) {
                logDebug("API retornou 401 - Token inválido/expirado.");
                sessionStorage.removeItem(TOKEN_STORAGE_KEY);
                sessionStorage.removeItem(TOKEN_TYPE_STORAGE_KEY);
                showDashboardMessage('Sessão inválida ou expirada. Por favor, faça login novamente.', true, false);
                setTimeout(() => window.location.href = 'admin_login.html', REDIRECT_DELAY + 1000);
                return null;
            }
            if (response.status === 204) {
                logDebug(`API Call Success (204 No Content): ${method} ${fullUrl}`);
                return { success: true, status: 204 };
            }
            const data = await response.json();
            logDebug(`API Response (${response.status}): ${method} ${fullUrl}`, data);
            if (!response.ok) {
                throw new Error(data.detail || `Erro HTTP ${response.status}`);
            }
            return data;
        } catch (error) {
            console.error(`Erro na chamada API para ${fullUrl} (${method}):`, error);
            showDashboardMessage(`Erro na API: ${error.message || 'Falha na comunicação.'}`, true);
            return null;
        }
    }

    async function loadCurrentAdminInfo() {
        const adminData = await fetchApi('/me');
        if (adminData && loggedInUserElement) {
            loggedInUserElement.textContent = `Admin: ${adminData.username}`;
            navigateToSection('overview'); // Carrega a visão geral por padrão
        } else if (mainDashboardContentElement && !adminData) {
            mainDashboardContentElement.innerHTML = "<p>Não foi possível carregar informações do administrador.</p>";
        }
    }

    // --- Seção Gerenciar Administradores ---
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
                            </div>
                        </li>`;
                });
                html += '</ul>';
            }
        } else {
            html += '<p>Erro ao carregar lista de administradores ou nenhum encontrado.</p>';
        }
        html += '</div>'; // Fim de .admin-list
        html += `<div class="form-section" id="adminFormContainer"></div>`; // Container para formulários
        if (mainDashboardContentElement) mainDashboardContentElement.innerHTML = html;
        renderAdminForm('create'); // Renderiza o formulário de criação por padrão
    }
    
    function renderAdminForm(mode = 'create', adminData = {}) {
        const formContainer = document.getElementById('adminFormContainer');
        if (!formContainer) {
            logDebug("Container de formulário de admin não encontrado.");
            return;
        }

        const isEditMode = mode === 'edit';
        const title = isEditMode ? `Editar Administrador: ${adminData.username || 'ID: '+adminData.id?.substring(0,8)}` : 'Criar Novo Administrador';
        const submitButtonText = isEditMode ? 'Salvar Alterações' : 'Criar Administrador';
        const hwidNote = isEditMode ? 
            (adminData.has_hwid ? "Fingerprint já registrado (digite novo para alterar/limpar)" : "Nenhum Fingerprint registrado (digite para adicionar)")
            : "Identificador do Cliente (Fingerprint - opcional no cadastro)";

        let formHtml = `<h4>${title}</h4>`;
        formHtml += `<form id="adminUpsertForm" data-mode="${mode}" data-id="${isEditMode ? adminData.id : ''}" novalidate>`;
        formHtml += `<div class="form-group">
                        <label for="adminUsername">Username:</label>
                        <input type="text" id="adminUsername" value="${isEditMode ? adminData.username : ''}" placeholder="Pelo menos 3 caracteres" required autocomplete="off">
                     </div>`;
        formHtml += `<div class="form-group">
                        <label for="adminPassword">${isEditMode ? 'Nova Senha (deixe em branco para não alterar)' : 'Senha:'}</label>
                        <input type="password" id="adminPassword" placeholder="Pelo menos 8 caracteres" ${!isEditMode ? 'required' : ''} autocomplete="new-password">
                     </div>`;
        if (isEditMode) {
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
                        <input type="text" id="adminClientFingerprint" placeholder="Gerado pelo navegador ou 'CLEAR_HWID' para limpar" autocomplete="off">
                        <small>Ao editar: preencher substitui; deixar em branco mantém; 'CLEAR_HWID' remove.</small>
                     </div>`;
        formHtml += `<button type="submit" id="adminUpsertButton" class="button">${submitButtonText}</button>`;
        if (isEditMode) {
            formHtml += `<button type="button" id="cancelEditAdminButton" class="button" style="margin-left: 10px; background-color: #7f8c8d;">Cancelar</button>`;
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
        if (password) {
            if (password.length > 0 && password.length < 8) { // Validação se senha foi digitada e é curta
                showDashboardMessage('A nova senha (se fornecida) deve ter pelo menos 8 caracteres.', true);
                if (upsertButton) upsertButton.disabled = false;
                return;
            }
            payload.password = password;
        } else if (mode === 'create') {
             showDashboardMessage('Senha é obrigatória para criar um novo administrador.', true);
             if (upsertButton) upsertButton.disabled = false;
             return;
        }
        
        if (client_fingerprint_input.toUpperCase() === "CLEAR_HWID") {
            payload.client_hwid_identifier = null; 
        } else if (client_fingerprint_input) {
            payload.client_hwid_identifier = client_fingerprint_input;
        } else if (mode === 'create' && !client_fingerprint_input) { // Para criação, se em branco, envia null.
            payload.client_hwid_identifier = null;
        }
        // Se em branco no modo de edição e não for CLEAR_HWID, o campo não é enviado no payload
        // para que o backend não o altere (o `admin_update_data.model_dump(exclude_unset=True)` cuida disso).

        let shortEndpoint = '/administrators';
        let method = 'POST';

        if (mode === 'edit') {
            shortEndpoint += `/${adminId}`;
            method = 'PUT';
            const statusValue = document.getElementById('adminStatus').value;
            payload.status = statusValue;
        }

        const result = await fetchApi(shortEndpoint, method, payload);

        if (result && (result.id || result.success)) {
            showDashboardMessage(`Administrador ${mode === 'edit' ? 'atualizado' : 'criado'} com sucesso!`, false);
            navigateToSection('manageAdmins');
        } else {
            showDashboardMessage(`Falha ao ${mode === 'edit' ? 'atualizar' : 'criar'} administrador. Verifique o console para detalhes ou mensagens da API.`, true);
        }
        if (upsertButton) upsertButton.disabled = false;
    }
    
    // --- Seção de Logs da API ---
    function renderApiLogsSection(logs, currentFilters = {}) {
        let html = '<h3>Logs da API</h3>';
        html += `
            <div class="log-filters form-section">
                <input type="text" id="logFilterPath" placeholder="Path contém..." value="${currentFilters.path_contains || ''}">
                <input type="number" id="logFilterStatus" placeholder="Status Code" value="${currentFilters.status_code || ''}" style="width: 120px;">
                <select id="logFilterMethod">
                    <option value="" ${!currentFilters.method ? 'selected' : ''}>Todos Métodos</option>
                    <option value="GET" ${currentFilters.method === 'GET' ? 'selected' : ''}>GET</option>
                    <option value="POST" ${currentFilters.method === 'POST' ? 'selected' : ''}>POST</option>
                    <option value="PUT" ${currentFilters.method === 'PUT' ? 'selected' : ''}>PUT</option>
                    <option value="DELETE" ${currentFilters.method === 'DELETE' ? 'selected' : ''}>DELETE</option>
                    <option value="HEAD" ${currentFilters.method === 'HEAD' ? 'selected' : ''}>HEAD</option>
                    <option value="OPTIONS" ${currentFilters.method === 'OPTIONS' ? 'selected' : ''}>OPTIONS</option>
                </select>
                <button id="applyLogFiltersButton" class="button">Filtrar</button>
                <button id="clearLogFiltersButton" class="button" style="background-color: #7f8c8d;">Limpar</button>
            </div>
        `;
        html += '<div class="api-log-list-container"><table class="api-log-table">';
        html += `<thead><tr><th>Timestamp</th><th>Método</th><th>Path</th><th>Status</th><th>IP</th><th>Usuário/Admin</th><th>Tags</th><th>Tempo(ms)</th><th>Erro</th></tr></thead><tbody>`;
        if (logs && Array.isArray(logs)) {
            if (logs.length === 0) {
                html += '<tr><td colspan="9" style="text-align:center; padding: 20px;">Nenhum log encontrado.</td></tr>';
            } else {
                logs.forEach(log => {
                    const ts = new Date(log.timestamp).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'medium' });
                    const userId = log.user_id ? `U: ${log.user_id.substring(0,6)}..` : '';
                    const adminId = log.admin_id ? `Adm: ${log.admin_id.substring(0,6)}..` : '';
                    const idDisplay = userId || adminId || 'Anon';
                    const tagsDisplay = log.tags ? log.tags.join(', ') : '-';
                    let statusClass = 'status-info';
                    if (log.status_code >= 500) statusClass = 'status-error-server';
                    else if (log.status_code >= 400) statusClass = 'status-error-client';
                    else if (log.status_code >= 300) statusClass = 'status-redirect';
                    else if (log.status_code >= 200) statusClass = 'status-success';
                    html += `<tr>
                        <td>${ts}</td>
                        <td><span class="log-method log-method-${(log.method || 'UNKNOWN').toLowerCase()}">${log.method || '?'}</span></td>
                        <td class="log-path">${log.path || '?'}</td>
                        <td><span class="log-status ${statusClass}">${log.status_code || '?'}</span></td>
                        <td>${log.client_host || '?'}</td><td>${idDisplay}</td>
                        <td class="log-tags">${tagsDisplay}</td><td>${log.processing_time_ms?.toFixed(1) || '-'}</td>
                        <td class="log-error">${log.error_message || '-'}</td>
                    </tr>`;
                });
            }
        } else {
            html += '<tr><td colspan="9" style="text-align:center; padding: 20px;">Erro ao carregar logs.</td></tr>';
        }
        html += '</tbody></table></div>';
        return html;
    }

    async function loadAndRenderApiLogs(filters = { skip: 0, limit: 50 }) {
        if (!mainDashboardContentElement) return;
        mainDashboardContentElement.innerHTML = "<p>Carregando logs da API...</p>";
        let queryParams = `?skip=${filters.skip || 0}&limit=${filters.limit || 50}`;
        if (filters.method) queryParams += `&method=${filters.method}`;
        if (filters.status_code) queryParams += `&status_code=${filters.status_code}`; // No backend, o alias é status_code
        if (filters.path_contains) queryParams += `&path_contains=${encodeURIComponent(filters.path_contains)}`;
        const logs = await fetchApi(`/logs/api${queryParams}`);
        mainDashboardContentElement.innerHTML = renderApiLogsSection(logs, filters);
        document.getElementById('applyLogFiltersButton')?.addEventListener('click', () => {
            const currentFilters = {
                path_contains: document.getElementById('logFilterPath').value.trim(),
                status_code: document.getElementById('logFilterStatus').value.trim(), // Nome do campo no objeto de filtros
                method: document.getElementById('logFilterMethod').value,
                skip: 0, limit: 50
            };
            for (const key in currentFilters) {
                if (currentFilters[key] === "" || currentFilters[key] === null) delete currentFilters[key];
            }
            loadAndRenderApiLogs(currentFilters);
        });
        document.getElementById('clearLogFiltersButton')?.addEventListener('click', () => loadAndRenderApiLogs());
    }

    // --- Navegação e Ações ---
    async function navigateToSection(sectionName) {
        logDebug("Navegando para a seção:", sectionName);
        if (!mainDashboardContentElement) return;
        mainDashboardContentElement.innerHTML = `<p>Carregando seção ${sectionName}...</p>`;
        document.querySelectorAll('.dashboard-nav button').forEach(btn => btn.classList.remove('active'));
        document.querySelector(`.dashboard-nav button[data-section="${sectionName}"]`)?.classList.add('active');
        if (sectionName === 'manageAdmins') {
            const admins = await fetchApi('/administrators');
            renderManageAdminsSection(admins);
        } else if (sectionName === 'apiLogs') {
            await loadAndRenderApiLogs();
        } else { 
            mainDashboardContentElement.innerHTML = '<h3>Visão Geral</h3><p>Bem-vindo ao painel de administração.</p>';
        }
    }
    
    function handleDashboardMainActions(event) {
        const target = event.target;
        if (target.classList.contains('edit-admin')) {
            event.preventDefault();
            const adminId = target.dataset.id;
            fetchApi(`/administrators/${adminId}`)
                .then(adminData => {
                    if(adminData) {
                        renderAdminForm('edit', {
                            id: adminData.id,
                            username: adminData.username,
                            status: adminData.status,
                            has_hwid: !!adminData.client_hwid_identifier_hash
                        });
                    } else {
                        showDashboardMessage("Não foi possível carregar dados do administrador para edição.", true);
                    }
                });
        }
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
            showDashboardMessage('Saindo do sistema...', false, false);
            sessionStorage.removeItem(TOKEN_STORAGE_KEY);
            sessionStorage.removeItem(TOKEN_TYPE_STORAGE_KEY);
            setTimeout(() => { window.location.href = 'admin_login.html'; }, REDIRECT_DELAY / 2);
        });
    }

    if (token) {
        loadCurrentAdminInfo();
    } else {
        window.location.href = 'admin_login.html';
    }
});
