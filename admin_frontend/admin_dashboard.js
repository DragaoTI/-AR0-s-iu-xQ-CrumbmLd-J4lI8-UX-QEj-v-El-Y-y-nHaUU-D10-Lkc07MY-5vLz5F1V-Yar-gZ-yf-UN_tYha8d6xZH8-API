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
                if (dashboardMessageElement.textContent === message) { // Só limpa se for a mesma mensagem
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
        // (Código da sua função renderManageAdminsSection da resposta anterior)
        // ... (cole aqui o código completo de renderManageAdminsSection, renderAdminForm, 
        //      handleAdminUpsertSubmit, e handleDashboardMainActions para 'edit-admin')
        // Certifique-se que ela chama renderAdminForm('create') no final
        // e adiciona o listener para handleDashboardMainActions.
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
        html += '</div>';
        html += `<div class="form-section" id="adminFormContainer"></div>`;
        if (mainDashboardContentElement) mainDashboardContentElement.innerHTML = html;
        renderAdminForm('create');
    }
    
    function renderAdminForm(mode = 'create', adminData = {}) {
        // (Código da sua função renderAdminForm da resposta anterior)
        // ... (cole aqui)
        const formContainer = document.getElementById('adminFormContainer');
        if (!formContainer) return;

        const isEditMode = mode === 'edit';
        const title = isEditMode ? `Editar Administrador: ${adminData.username}` : 'Criar Novo Administrador';
        const submitButtonText = isEditMode ? 'Salvar Alterações' : 'Criar Administrador';
        const hwidNote = isEditMode ? 
            (adminData.has_hwid ? "Fingerprint já registrado (digite novo para alterar/limpar)" : "Nenhum Fingerprint registrado (digite para adicionar)")
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
                        <input type="text" id="adminClientFingerprint" placeholder="Gerado pelo navegador ou 'CLEAR_HWID' para limpar">
                        <small>Ao editar: preencher substitui; deixar em branco mantém; 'CLEAR_HWID' remove.</small>
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
                cancelButton.addEventListener('click', () => renderAdminForm('create'));
            }
        }
    }

    async function handleAdminUpsertSubmit(event) {
        // (Código da sua função handleAdminUpsertSubmit da resposta anterior)
        // ... (cole aqui)
        event.preventDefault();
        const form = event.target;
        const mode = form.dataset.mode;
        const adminId = form.dataset.id;
        const upsertButton = document.getElementById('adminUpsertButton');
        if (upsertButton) upsertButton.disabled = true;

        const username = document.getElementById('adminUsername').value.trim();
        const password = document.getElementById('adminPassword').value;
        const client_fingerprint_input = document.getElementById('adminClientFingerprint').value.trim();
        
        const payload = { username };
        if (password) payload.password = password;
        
        if (client_fingerprint_input.toUpperCase() === "CLEAR_HWID") {
            payload.client_hwid_identifier = null; 
        } else if (client_fingerprint_input) {
            payload.client_hwid_identifier = client_fingerprint_input;
        } else if (mode === 'create') {
            payload.client_hwid_identifier = null;
        }

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
        }
        if (upsertButton) upsertButton.disabled = false;
    }
    
    // --- Seção de Logs da API ---
    function renderApiLogsSection(logs) {
        let html = '<h3>Logs da API</h3>';
        html += `
            <div class="log-filters form-section" style="margin-bottom: 20px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                <input type="text" id="logFilterPath" placeholder="Path contém..." style="flex-grow:1; min-width: 150px;">
                <input type="number" id="logFilterStatus" placeholder="Status" style="width: 100px;">
                <select id="logFilterMethod" style="min-width: 120px;">
                    <option value="">Todos Métodos</option>
                    <option value="GET">GET</option>
                    <option value="POST">POST</option>
                    <option value="PUT">PUT</option>
                    <option value="DELETE">DELETE</option>
                </select>
                <button id="applyLogFiltersButton" class="button">Filtrar</button>
                <button id="clearLogFiltersButton" class="button" style="background-color: #95a5a6;">Limpar Filtros</button>
            </div>
        `;

        html += '<div class="api-log-list" style="max-height: 600px; overflow-y: auto; border: 1px solid #ccc; padding: 10px; background-color: #fdfdfd;">';
        if (logs && Array.isArray(logs)) {
            if (logs.length === 0) {
                html += '<p>Nenhum log encontrado para os filtros aplicados.</p>';
            } else {
                html += '<ul style="font-family: monospace; font-size: 0.8em; list-style: none; padding:0;">'; // Tamanho de fonte menor para logs
                logs.forEach(log => {
                    const ts = new Date(log.timestamp).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'medium' });
                    const userDisplay = log.user_id ? `User: ${log.user_id.substring(0,8)}` : (log.admin_id ? `AdmPanel: ${log.admin_id.substring(0,8)}` : 'Anon');
                    const tagsDisplay = log.tags ? log.tags.join(', ') : 'N/A';
                    let statusClass = '';
                    if (log.status_code >= 500) statusClass = 'log-status-server-error';
                    else if (log.status_code >= 400) statusClass = 'log-status-client-error';
                    else if (log.status_code >= 300) statusClass = 'log-status-redirect';
                    else if (log.status_code >= 200) statusClass = 'log-status-success';

                    html += `
                        <li style="border-bottom: 1px dotted #e0e0e0; padding: 6px 2px; margin-bottom: 6px; word-break: break-all;">
                            <strong class="${statusClass}">[${ts}] ${log.method} ${log.path} ➔ ${log.status_code}</strong> (${log.processing_time_ms?.toFixed(1)}ms)<br>
                            <small>IP: ${log.client_host} | ${userDisplay} | Tags: [${tagsDisplay}]</small><br>
                            <small title="${log.user_agent || ''}">UA: ${log.user_agent?.substring(0, 60) || 'N/A'}...</small>
                            ${log.error_message ? `<br><small style="color: #c0392b; font-weight: bold;">ErroMsg: ${log.error_message}</small>` : ''}
                        </li>`;
                });
                html += '</ul>';
            }
        } else {
            html += '<p>Erro ao carregar logs ou formato inesperado.</p>';
        }
        html += '</div>';
        return html;
    }

    async function loadAndRenderApiLogs(filters = { skip: 0, limit: 50 }) { // Adiciona skip/limit padrão
        if (!mainDashboardContentElement) return;
        mainDashboardContentElement.innerHTML = "<p>Carregando logs da API...</p>";

        let queryParams = `?skip=${filters.skip || 0}&limit=${filters.limit || 50}`;
        if (filters.method) queryParams += `&method=${filters.method}`;
        if (filters.status_code_filter) queryParams += `&status_code_filter=${filters.status_code_filter}`; // Nome do param do backend
        if (filters.path_contains) queryParams += `&path_contains=${encodeURIComponent(filters.path_contains)}`;
        
        const logs = await fetchApi(`/logs/api${queryParams}`);
        mainDashboardContentElement.innerHTML = renderApiLogsSection(logs); // Passa os logs para a função de renderização

        // Adicionar listeners aos filtros DEPOIS que eles foram renderizados
        document.getElementById('applyLogFiltersButton')?.addEventListener('click', () => {
            const pathFilter = document.getElementById('logFilterPath').value;
            const statusFilter = document.getElementById('logFilterStatus').value;
            const methodFilter = document.getElementById('logFilterMethod').value;
            loadAndRenderApiLogs({ 
                path_contains: pathFilter, 
                status_code_filter: statusFilter, // Usa o nome correto do parâmetro
                method: methodFilter 
            });
        });
        document.getElementById('clearLogFiltersButton')?.addEventListener('click', () => {
            document.getElementById('logFilterPath').value = '';
            document.getElementById('logFilterStatus').value = '';
            document.getElementById('logFilterMethod').value = '';
            loadAndRenderApiLogs(); // Carrega com filtros limpos
        });
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
        } else { // overview ou default
            mainDashboardContentElement.innerHTML = '<h3>Visão Geral</h3><p>Bem-vindo ao painel de administração.</p>';
        }
    }
    
    function handleDashboardMainActions(event) {
        const target = event.target;
        // Delegação para botões de editar admin
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
            showDashboardMessage('Saindo do sistema...', false, false); // Não auto-limpar
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
