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

    async function fetchApi(shortEndpoint, method = 'GET', body = null) { // shortEndpoint é ex: '/me' ou '/administrators'
        const headers = {
            'Authorization': `${tokenType} ${token}`,
            'Content-Type': 'application/json',
        };
        const config = { method, headers };
        if (body) {
            config.body = JSON.stringify(body);
        }

        // USA A NOVA CONSTANTE API_PANEL_ENDPOINTS_BASE
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
        const adminData = await fetchApi('/me'); // shortEndpoint
        if (adminData && loggedInUserElement) {
            loggedInUserElement.textContent = `Admin: ${adminData.username}`;
            navigateToSection('manageAdmins');
        } else if (mainDashboardContentElement && !adminData) {
            mainDashboardContentElement.innerHTML = "<p>Não foi possível carregar informações do administrador.</p>";
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
    
    async function navigateToSection(sectionName) {
        logDebug("Navegando para a seção:", sectionName);
        if (!mainDashboardContentElement) return;
        mainDashboardContentElement.innerHTML = `<p>Carregando seção ${sectionName}...</p>`;

        if (sectionName === 'manageAdmins') {
            const admins = await fetchApi('/administrators'); // shortEndpoint
            renderManageAdminsSection(admins);
        } else {
            mainDashboardContentElement.innerHTML = '<h3>Visão Geral</h3><p>Bem-vindo ao painel. Selecione uma opção.</p>';
        }
    }
    
    function handleDashboardMainActions(event) {
        const target = event.target;
        if (target.classList.contains('edit-admin')) {
            event.preventDefault();
            const adminId = target.dataset.id;
            fetchApi(`/administrators/${adminId}`) // shortEndpoint
                .then(adminData => {
                    if(adminData) {
                        renderAdminForm('edit', {
                            id: adminData.id,
                            username: adminData.username,
                            status: adminData.status,
                            has_hwid: !!adminData.client_hwid_identifier_hash
                        });
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
            showDashboardMessage('Saindo do sistema...', false, 10000);
            sessionStorage.removeItem(TOKEN_STORAGE_KEY);
            sessionStorage.removeItem(TOKEN_TYPE_STORAGE_KEY);
            setTimeout(() => {
                window.location.href = 'admin_login.html';
            }, REDIRECT_DELAY / 2);
        });
    }

    if (token) {
        loadCurrentAdminInfo();
    } else {
        window.location.href = 'admin_login.html';
    }
});
