// admin_frontend/admin_app_config.js

// MUITO IMPORTANTE: Substitua pela URL real da sua API no Render
// Exemplo: const API_BASE_URL = 'https://minha-api-admin.onrender.com/api/v1';
const API_BASE_URL = 'http://localhost:8000/api/v1'; // Para desenvolvimento local com FastAPI na porta 8000

// Chaves para o sessionStorage (mais seguro que localStorage para tokens de sessão)
const TOKEN_STORAGE_KEY = 'adminAuthToken_v1'; // Adicionar versão caso precise limpar tokens antigos
const TOKEN_TYPE_STORAGE_KEY = 'adminAuthTokenType_v1';

// Opções para o FingerprintJS (se estiver usando)
const FP_OPTIONS = {
    // Você pode customizar as fontes de dados que o FingerprintJS usa.
    // Veja a documentação: https://fingerprint.com/github/
    // Exemplo:
    // मुरसानmurmurHash: true, // Usa uma técnica de hashing mais robusta
    // debug: false, // Defina como true para ver logs do FingerprintJS no console
};
