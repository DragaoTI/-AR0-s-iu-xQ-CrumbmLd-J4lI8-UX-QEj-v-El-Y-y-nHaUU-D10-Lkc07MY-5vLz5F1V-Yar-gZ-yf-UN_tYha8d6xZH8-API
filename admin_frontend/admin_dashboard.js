// admin_frontend/admin_dashboard.js

// API_BASE_URL, TOKEN_STORAGE_KEY, TOKEN_TYPE_STORAGE_KEY
// são definidos em admin_app_config.js e já devem estar carregados.

document.addEventListener('DOMContentLoaded', () => {
    const token = sessionStorage.getItem(TOKEN_STORAGE_KEY);
    const tokenType = sessionStorage.getItem(TOKEN_TYPE_STORAGE_KEY) || 'Bearer';
    const mainContentElement = document.getElementById('mainContent');
    const loggedInUserElement = document.getElementById('loggedInUser');
    const logoutButton = document.getElementById('logoutButton');
    const dashboardMessageElement = document.getElementById('dashboardMessage');

    function showDashboardMessage(message, isError = false, duration = 5000) {
        if (!dashboardMessageElement) return;
        dashboardMessageElement.textContent = message;
        dashboardMessageElement.className = 'message-area ' + (isError ? 'error-message' : 'success-message');
        dashboardMessageElement.style.display = message ? 'block' : 'none';
        
        if (message) {
            setTimeout(() => {
                dashboardMessageElement.style.display = 'none';
            }, duration);
        }
    }

    if (!token) {
        // Se não há token, não deve nem estar nesta página
        window.location.href = 'admin_login.html';
        return;
    }

    async function fetchApi(endpoint, method = 'GET', body = null) {
        const headers = {
            'Authorization': `${tokenType} ${token}`,
            'Content-Type': 'application/json',
        };
        const config = {
            method,
            headers,
            // mode: 'cors', // Geralmente o padrão, mas explícito se necessário
            // cache: 'no-cache', // Para garantir dados frescos
        };
        if (body) {
            config.body = JSON.stringify(body);
        }

        try {
            const response = await fetch(`${API_BASE_URL}${endpoint}`, config);

            if (response.status === 401) {
                sessionStorage.removeItem(TOKEN_STORAGE_KEY);
                sessionStorage.removeItem(TOKEN_TYPE_STORAGE_KEY);
                showDashboardMessage('Sessão inválida ou expirada. Redirecionando para login...', true, 3000);
                setTimeout(() => window.location.href = 'admin_login.html', 3000);
                return null;
            }

            // Para respostas No Content (ex: DELETE bem-sucedido)
            if (response.status === 204) {
                return { success: true, status: 204 };
            }

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || `Erro HTTP ${response.status}`);
            }
            return data;
        } catch (error) {
            console.error(`Erro na chamada API para ${endpoint}:`, error);
            showDashboardMessage(`Erro na comunicação com a API: ${error.message}`, true);
            return null;
        }
    }

    async function loadAdminInfo() {
        const adminData = await fetchApi('/admin-panel/me');
        if (adminData && loggedInUserElement) {
            loggedInUserElement.textContent = `Usuário: ${adminData.username}`;
            loadAdministratorsSection(); // Carrega a seção de administradores após pegar dados do usuário
        } else if (mainContentElement) {
            mainContentElement.innerHTML = "<p>Falha ao carregar informações do administrador.</p>";
        }
    }

    function renderAdministratorsList(admins) {
        let listHtml = '<h4>Lista de Administradores</h4>';
        if (admins && Array.isArray(admins) && admins.length > 0) {
            listHtml += '<ul>';
            admins.forEach(admin => {
                listHtml += `
                    <li>
                        <span>${admin.username} (ID: ${admin.id.substring(0,8)}... Status: ${admin.status})</span>
                        <span class="actions">
                            <a href="#" class="edit-admin" data-id="${admin.id}" data-username="${admin.username}" data-status="${admin.status}" data-hwid="${admin.client_hwid_identifier_hash || ''}">Editar</a>
                            <!-- Adicionar botão de excluir se necessário, com confirmação -->
                        </span>
                    </li>`;
            });
            listHtml += '</ul>';
        } else {
            listHtml += '<p>Nenhum administrador encontrado.</p>';
        }
        return listHtml;
    }
    
    function renderCreateAdminForm() {
        return `
            <h4>Criar Novo Administrador</h4>
            <form id="createAdminForm" novalidate>
                <div class="form-group">
                    <label for="newAdminUsername">Username:</label>
                    <input type="text" id="newAdminUsername" placeholder="Pelo menos 3 caracteres" required>
                </div>
                <div class="form-group">
                    <label for="newAdminPassword">Senha:</label>
                    <input type="password" id="newAdminPassword" placeholder="Pelo menos 8 caracteres" required>
                </div>
                <div class="form-group">
                    <label for="newAdminHwid">Identificador do Cliente (HWID - opcional no cadastro):</label>
                    <input type="text" id="newAdminHwid" placeholder="Deixe em branco se não aplicável agora">
                </div>
                <button type="submit" id="createAdminButton">Criar Admin</button>
            </form>
        `;
    }
    
    // Placeholder para formulário de edição
    function renderEditAdminForm(admin = {}) {
         return `
            <h4>Editar Administrador: ${admin.username || 'Novo'}</h4>
            <form id="editAdminForm" data-id="${admin.id || ''}" novalidate>
                 <input type="hidden" id="editAdminId" value="${admin.id || ''}">
                <div class="form-group">
                    <label for="editAdminUsername">Username:</label>
                    <input type="text" id="editAdminUsername" value="${admin.username || ''}" placeholder="Pelo menos 3 caracteres" required>
                </div>
                <div class="form-group">
                    <label for="editAdminPassword">Nova Senha (deixe em branco para não alterar):</label>
                    <input type="password" id="editAdminPassword" placeholder="Pelo menos 8 caracteres">
                </div>
                <div class="form-group">
                    <label for="editAdminHwid">Novo Identificador Cliente (HWID - opcional):</label>
                    <input type="text" id="editAdminHwid" value="${admin.client_hwid_identifier_to_show || ''}" placeholder="Deixe em branco para não alterar ou limpar">
                     <small>Se preenchido, substituirá o HWID atual. Deixe em branco para manter o HWID atual ou se o admin ainda não tiver um.</small>
                </div>
                 <div class="form-group">
                    <label for="editAdminStatus">Status:</label>
                    <select id="editAdminStatus">
                        <option value="active" ${admin.status === 'active' ? 'selected' : ''}>Ativo</option>
                        <option value="inactive" ${admin.status === 'inactive' ? 'selected' : ''}>Inativo</option>
                    </select>
                </div>
                <button type="submit" id="saveAdminButton">Salvar Alterações</button>
                <button type="button" id="cancelEditButton">Cancelar</button>
            </form>
        `;
    }


    async function loadAdministratorsSection() {
        if (!mainContentElement) return;
        mainContentElement.innerHTML = "<p>Carregando administradores...</p>"; // Feedback de carregamento

        const admins = await fetchApi('/admin-panel/administrators');
        let sectionHtml = renderAdministratorsList(admins);
        sectionHtml += renderCreateAdminForm();
        sectionHtml += '<div id="editAdminFormContainer" style="margin-top: 20px;"></div>'; // Container para o form de edição
        
        mainContentElement.innerHTML = sectionHtml;

        const createAdminForm = document.getElementById('createAdminForm');
        if (createAdminForm) {
            createAdminForm.addEventListener('submit', handleCreateAdminSubmit);
        }
        // Delegação de eventos para links/botões dinâmicos
        mainContentElement.addEventListener('click', handleDashboardActions);
    }

    async function handleCreateAdminSubmit(event) {
        event.preventDefault();
        const createButton = document.getElementById('createAdminButton');
        if(createButton) createButton.disabled = true;

        const username = document.getElementById('newAdminUsername').value.trim();
        const password = document.getElementById('newAdminPassword').value;
        const client_hwid_identifier = document.getElementById('newAdminHwid').value.trim() || null;

        if (!username || !password) {
            showDashboardMessage("Username e senha são obrigatórios para criar um administrador.", true);
            if(createButton) createButton.disabled = false;
            return;
        }

        const result = await fetchApi('/admin-panel/administrators', 'POST', {
            username, password, client_hwid_identifier
        });

        if (result && result.id) {
            showDashboardMessage('Administrador criado com sucesso!', false);
            loadAdministratorsSection(); // Recarrega a seção inteira
        } else {
            // A mensagem de erro específica já deve ter sido mostrada por fetchApi
        }
        if(createButton) createButton.disabled = false;
    }
    
    function populateEditForm(adminId, currentUsername, currentStatus, currentHwidHash) {
        const editContainer = document.getElementById('editAdminFormContainer');
        if(!editContainer) return;
        
        // O HWID hash não deve ser mostrado diretamente para o usuário para edição direta.
        // O usuário digitaria um novo identificador que seria hasheado no backend.
        // Se você quer mostrar que um HWID está registrado, use um placeholder ou uma mensagem.
        const hwidPlaceholder = currentHwidHash ? "HWID Registrado (digite novo para alterar)" : "Nenhum HWID registrado";

        editContainer.innerHTML = renderEditAdminForm({
            id: adminId,
            username: currentUsername,
            status: currentStatus,
            client_hwid_identifier_to_show: "" // Campo para o usuário digitar um novo HWID
        });
        
        const editAdminForm = document.getElementById('editAdminForm');
        if(editAdminForm) {
            editAdminForm.addEventListener('submit', handleEditAdminSubmit);
            document.getElementById('cancelEditButton').addEventListener('click', () => {
                editContainer.innerHTML = ''; // Limpa o formulário de edição
            });
        }
    }

    async function handleEditAdminSubmit(event) {
        event.preventDefault();
        const saveButton = document.getElementById('saveAdminButton');
        if(saveButton) saveButton.disabled = true;

        const adminId = document.getElementById('editAdminId').value;
        const username = document.getElementById('editAdminUsername').value.trim();
        const password = document.getElementById('editAdminPassword').value; // Senha opcional
        const client_hwid_identifier = document.getElementById('editAdminHwid').value.trim() || null; // HWID opcional
        const status = document.getElementById('editAdminStatus').value;

        const updateData = { status }; // Status é sempre enviado
        if (username) updateData.username = username;
        if (password) updateData.password = password; // Envia só se preenchido
        if (client_hwid_identifier !== null) { // Permite enviar string vazia para limpar, ou novo valor
             updateData.client_hwid_identifier = client_hwid_identifier === "" ? null : client_hwid_identifier;
        }


        const result = await fetchApi(`/admin-panel/administrators/${adminId}`, 'PUT', updateData);
        if (result && result.id) {
            showDashboardMessage('Administrador atualizado com sucesso!', false);
            document.getElementById('editAdminFormContainer').innerHTML = ''; // Limpa form
            loadAdministratorsSection(); // Recarrega
        } else {
            // Erro já mostrado por fetchApi
        }
        if(saveButton) saveButton.disabled = false;
    }


    function handleDashboardActions(event) {
        if (event.target.classList.contains('edit-admin')) {
            event.preventDefault();
            const adminId = event.target.dataset.id;
            const username = event.target.dataset.username;
            const status = event.target.dataset.status;
            const hwidHash = event.target.dataset.hwid; // Este é o HASH, não mostrar diretamente.
            populateEditForm(adminId, username, status, hwidHash);
        }
        // Adicionar handler para deletar admin aqui
    }

    if (logoutButton) {
        logoutButton.addEventListener('click', async () => {
            showDashboardMessage('Saindo...', false, 10000); // Mensagem longa enquanto processa
            // Se você tem um endpoint de logout na API para invalidar tokens ou registrar, chame-o.
            // Ex: await fetchApi('/admin-panel/auth/logout', 'POST'); 
            // Como não temos um para JWTs stateless, apenas limpamos localmente.
            
            sessionStorage.removeItem(TOKEN_STORAGE_KEY);
            sessionStorage.removeItem(TOKEN_TYPE_STORAGE_KEY);
            
            // Delay para garantir que a mensagem é vista antes do redirecionamento
            setTimeout(() => {
                window.location.href = 'admin_login.html';
            }, 500);
        });
    }

    // Iniciar carregando informações do admin e outras seções
    if (token) {
        loadAdminInfo();
    }
});
