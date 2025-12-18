/**
 * Plante Uma Flor - PWA v3.0
 * Módulo de Autenticação
 * Gerencia login, logout e verificação de autenticação
 */

const Auth = {
    STORAGE_KEY: 'plante_uma_flor_auth',
    SESSION_KEY: 'plante_uma_flor_auth_session',
    _authCache: null, // Cache do estado de autenticação
    _cacheTimestamp: 0, // Timestamp do cache
    CACHE_DURATION: 5000, // Cache válido por 5 segundos
    
    /**
     * Inicializa o módulo de autenticação (lazy - apenas cache básico)
     */
    init() {
        // Inicialização lazy - apenas popular cache se houver credenciais
        // Não fazer parse completo para não bloquear
        const hasStored = localStorage.getItem(this.STORAGE_KEY) || 
                          sessionStorage.getItem(this.SESSION_KEY);
        if (hasStored) {
            this._authCache = true;
            this._cacheTimestamp = Date.now();
        } else {
            this._authCache = false;
            this._cacheTimestamp = Date.now();
        }
    },
    
    /**
     * Carrega credenciais salvas do localStorage
     */
    loadStoredCredentials() {
        try {
            const stored = localStorage.getItem(this.STORAGE_KEY);
            if (stored) {
                const data = JSON.parse(stored);
                console.log('📦 Credenciais encontradas no localStorage');
                return data;
            }
        } catch (error) {
            console.error('Erro ao carregar credenciais:', error);
        }
        return null;
    },
    
    /**
     * Faz login com usuário e senha
     * @param {string} username - Nome de usuário
     * @param {string} password - Senha
     * @param {boolean} remember - Se deve salvar credenciais
     * @returns {Promise<Object>} Resultado do login
     */
    async login(username, password, remember = false) {
        try {
            // Validar credenciais no backend
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Salvar credenciais
                const authData = {
                    username,
                    password, // Em produção, usar token JWT
                    timestamp: Date.now()
                };
                
                if (remember) {
                    localStorage.setItem(this.STORAGE_KEY, JSON.stringify(authData));
                } else {
                    sessionStorage.setItem(this.SESSION_KEY, JSON.stringify(authData));
                }
                
                // Atualizar cache
                this._authCache = true;
                this._cacheTimestamp = Date.now();
                
                // Atualizar indicadores de autenticação imediatamente após login
                if (typeof App !== 'undefined' && App.updateAuthIndicator) {
                    setTimeout(() => {
                        App.updateAuthIndicator();
                    }, 100);
                }
                
                return { success: true, message: 'Login realizado com sucesso' };
            } else {
                return { success: false, error: data.error || 'Credenciais inválidas' };
            }
        } catch (error) {
            console.error('Erro ao fazer login:', error);
            return { 
                success: false, 
                error: 'Erro ao conectar com o servidor. Verifique sua conexão.' 
            };
        }
    },
    
    /**
     * Faz logout e limpa credenciais
     */
    logout() {
        localStorage.removeItem(this.STORAGE_KEY);
        sessionStorage.removeItem(this.SESSION_KEY);
        
        // Limpar cache
        this._authCache = false;
        this._cacheTimestamp = Date.now();
        
        // Atualizar indicadores de autenticação após logout
        if (typeof App !== 'undefined' && App.updateAuthIndicator) {
            setTimeout(() => {
                App.updateAuthIndicator();
            }, 100);
        }
    },
    
    /**
     * Verifica se está autenticado (com cache e inicialização lazy)
     * @returns {boolean} True se autenticado
     */
    isAuthenticated() {
        // Se cache não foi inicializado, inicializar agora (lazy init)
        if (this._cacheTimestamp === 0) {
            this.init();
        }
        
        // Verificar se cache é válido
        const now = Date.now();
        if (this._authCache !== null && (now - this._cacheTimestamp) < this.CACHE_DURATION) {
            return this._authCache;
        }
        
        // Atualizar cache
        const stored = localStorage.getItem(this.STORAGE_KEY) || 
                      sessionStorage.getItem(this.SESSION_KEY);
        this._authCache = stored !== null;
        this._cacheTimestamp = now;
        
        return this._authCache;
    },
    
    /**
     * Obtém credenciais salvas
     * @returns {Object|null} Credenciais ou null
     */
    getCredentials() {
        try {
            const stored = localStorage.getItem(this.STORAGE_KEY) || 
                          sessionStorage.getItem(this.SESSION_KEY);
            if (stored) {
                return JSON.parse(stored);
            }
        } catch (error) {
            console.error('Erro ao obter credenciais:', error);
        }
        return null;
    },
    
    /**
     * Gera header Authorization para requisições HTTP Basic
     * @returns {Object} Headers com Authorization
     */
    getAuthHeader() {
        const creds = this.getCredentials();
        if (!creds) {
            return {};
        }
        
        // Criar Basic Auth header
        const credentials = btoa(`${creds.username}:${creds.password}`);
        return {
            'Authorization': `Basic ${credentials}`
        };
    },
    
    /**
     * Mostra prompt de senha quando necessário
     * @param {string} message - Mensagem a exibir
     * @returns {Promise<Object>} Credenciais ou null se cancelado
     */
    async promptPassword(message = 'Esta ação requer autenticação. Por favor, faça login.') {
        return new Promise((resolve) => {
            // Criar modal customizado para login
            const overlay = document.createElement('div');
            overlay.className = 'fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4';
            overlay.style.zIndex = '9999';
            
            const modal = document.createElement('div');
            modal.className = 'bg-white rounded-lg shadow-xl max-w-md w-full p-6';
            
            modal.innerHTML = `
                <h2 class="text-2xl font-bold text-gray-800 mb-4">
                    <i class="fas fa-lock text-primary"></i>
                    Autenticação Necessária
                </h2>
                <p class="text-gray-700 mb-4">${message}</p>
                <div class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">
                            <i class="fas fa-user"></i> Usuário
                        </label>
                        <input 
                            type="text" 
                            id="prompt-username" 
                            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary"
                            placeholder="admin"
                            value="admin"
                        >
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">
                            <i class="fas fa-key"></i> Senha
                        </label>
                        <input 
                            type="password" 
                            id="prompt-password" 
                            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary"
                            placeholder="Digite sua senha"
                            autofocus
                        >
                    </div>
                    <div class="flex items-center">
                        <input 
                            type="checkbox" 
                            id="prompt-remember" 
                            class="w-4 h-4 text-primary border-gray-300 rounded"
                        >
                        <label for="prompt-remember" class="ml-2 text-sm text-gray-700">
                            Lembrar-me
                        </label>
                    </div>
                </div>
                <div class="flex justify-end space-x-2 mt-6">
                    <button 
                        id="prompt-cancel"
                        class="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300"
                    >
                        Cancelar
                    </button>
                    <button 
                        id="prompt-submit"
                        class="px-4 py-2 bg-primary text-white rounded-lg hover:bg-secondary"
                    >
                        Entrar
                    </button>
                </div>
            `;
            
            overlay.appendChild(modal);
            document.body.appendChild(overlay);
            
            // Focar no campo de senha
            setTimeout(() => {
                const passwordInput = document.getElementById('prompt-password');
                if (passwordInput) passwordInput.focus();
            }, 100);
            
            // Handler de cancelar
            document.getElementById('prompt-cancel').addEventListener('click', () => {
                document.body.removeChild(overlay);
                resolve(null);
            });
            
            // Handler de submit
            document.getElementById('prompt-submit').addEventListener('click', async () => {
                const username = document.getElementById('prompt-username').value.trim();
                const password = document.getElementById('prompt-password').value.trim();
                const remember = document.getElementById('prompt-remember').checked;
                
                if (!username || !password) {
                    Notification.error('Por favor, preencha usuário e senha');
                    return;
                }
                
                const result = await Auth.login(username, password, remember);
                if (result.success) {
                    document.body.removeChild(overlay);
                    resolve({ username, password, remember });
                } else {
                    Notification.error(result.error || 'Credenciais inválidas');
                }
            });
            
            // Fechar ao clicar no overlay
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) {
                    document.body.removeChild(overlay);
                    resolve(null);
                }
            });
            
            // Fechar com ESC
            const escHandler = (e) => {
                if (e.key === 'Escape') {
                    document.body.removeChild(overlay);
                    document.removeEventListener('keydown', escHandler);
                    resolve(null);
                }
            };
            document.addEventListener('keydown', escHandler);
        });
    },
    
    /**
     * Verifica autenticação no servidor
     * @returns {Promise<boolean>} True se autenticado
     */
    async checkAuth() {
        try {
            const creds = this.getCredentials();
            if (!creds) {
                return false;
            }
            
            const response = await fetch('/api/auth/check', {
                headers: this.getAuthHeader()
            });
            
            const data = await response.json();
            return data.success && data.authenticated === true;
        } catch (error) {
            console.error('Erro ao verificar autenticação:', error);
            return false;
        }
    }
};

// Inicialização lazy - não executar automaticamente
// Será inicializado na primeira chamada de isAuthenticated()

