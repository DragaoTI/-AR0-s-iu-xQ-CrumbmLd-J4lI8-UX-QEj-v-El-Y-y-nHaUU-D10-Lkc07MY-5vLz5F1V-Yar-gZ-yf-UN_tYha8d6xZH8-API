// admin_frontend/admin_app_config.js

// URL base COMPLETA para os endpoints da API do painel de administração.
// Inclui o /api/v1 e o prefixo /admin-panel do router.
const API_PANEL_ENDPOINTS_BASE = 'https://four3nuihgv7834hgv783h8fvhn2847nrv8h3hn7.onrender.com/api/v1/admin-panel';
// Para desenvolvimento local, você pode ter:
// const API_PANEL_ENDPOINTS_BASE = 'http://localhost:8000/api/v1/admin-panel';

const TOKEN_STORAGE_KEY = 'adminAuthToken_fp_v2';
const TOKEN_TYPE_STORAGE_KEY = 'adminAuthTokenType_fp_v2';

const FP_JS_LOAD_OPTIONS = {};
const FP_JS_GET_OPTIONS = {};

const MESSAGE_TIMEOUT_DURATION = 5000;
const REDIRECT_DELAY = 1500;

// Mude para true para ver logs detalhados do frontend no console do navegador
const FRONTEND_DEBUG_MODE = false; 

function logDebug(...args) {
    if (FRONTEND_DEBUG_MODE) {
        console.log('[ADMIN_DEBUG]', ...args);
    }
}
