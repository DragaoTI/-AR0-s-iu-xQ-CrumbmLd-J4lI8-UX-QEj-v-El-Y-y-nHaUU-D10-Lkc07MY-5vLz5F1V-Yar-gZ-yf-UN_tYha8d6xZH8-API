// admin_frontend/admin_app_config.js

// MUITO IMPORTANTE: Substitua pela URL real da sua API no Render
// Exemplo: const API_BASE_URL = 'https://minha-api-admin.onrender.com/api/v1';
const API_BASE_URL = 'https://four3nuihgv7834hgv783h8fvhn2847nrv8h3hn7.onrender.com'; // Para desenvolvimento local com FastAPI na porta 8000
// Para desenvolvimento local, você pode ter algo como:
// const API_BASE_URL = 'http://localhost:8000/api/v1';

// Chaves para o sessionStorage (preferível ao localStorage para tokens de sessão)
const TOKEN_STORAGE_KEY = 'adminAuthToken_fp_v2'; // v2 para indicar mudança
const TOKEN_TYPE_STORAGE_KEY = 'adminAuthTokenType_fp_v2';

// Configurações para o FingerprintJS
// Você pode explorar as opções avançadas na documentação do FingerprintJS Pro/Source
// para obter um identificador mais estável e preciso se necessário.
const FP_JS_LOAD_OPTIONS = {
    // Exemplo: Se você tiver uma chave de API pública do FingerprintJS Pro
    // apiKey: "SUA_CHAVE_API_PUBLICA_FPJS_PRO", 
    // region: "eu" // se seus servidores estiverem na EU
};

const FP_JS_GET_OPTIONS = {
    // Opções para o método .get()
    // debug: true // Para ver informações detalhadas no console durante o desenvolvimento
};

// Tempo em milissegundos para mensagens de feedback desaparecerem
const MESSAGE_TIMEOUT_DURATION = 5000; // 5 segundos
const REDIRECT_DELAY = 1500; // 1.5 segundos para redirecionamentos após mensagens

// Habilitar ou desabilitar logs de debug no console do frontend
const FRONTEND_DEBUG_MODE = false; // Mude para true durante o desenvolvimento

function logDebug(...args) {
    if (FRONTEND_DEBUG_MODE) {
        console.log('[ADMIN_DEBUG]', ...args);
    }
}
