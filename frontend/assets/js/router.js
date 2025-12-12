/**
 * Plante Uma Flor - PWA v3.0
 * Client-Side Router - Navegação SPA
 */

const Router = {
    routes: {
        '/': () => Router.navigate('/painel'),
        '/login': () => Router.loadPage('login'),
        '/criar-pedido': () => Router.loadPage('criar-pedido'),
        '/painel': () => Router.loadPage('painel'),
        '/rota-entrega': () => Router.loadPage('rota-entrega')
    },

    currentRoute: null,

    /**
     * Inicializa o router
     */
    init() {
        // Listener para botões de voltar/avançar do navegador
        window.addEventListener('popstate', () => {
            this.loadRoute(window.location.pathname);
        });

        // Interceptar clicks em links
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-link]')) {
                e.preventDefault();
                this.navigate(e.target.getAttribute('href'));
            }
        });

        // Carregar rota inicial
        this.loadRoute(window.location.pathname);
    },

    /**
     * Navega para uma rota
     */
    navigate(path) {
        // Verificar se a rota requer autenticação
        if (path === '/criar-pedido') {
            if (typeof Auth === 'undefined' || !Auth.isAuthenticated()) {
                // Tentar pedir senha antes de navegar
                if (typeof Auth !== 'undefined') {
                    Auth.promptPassword('Para criar um pedido, é necessário fazer login.')
                        .then((creds) => {
                            if (creds) {
                                // Se autenticou, navegar
                                window.history.pushState({}, '', path);
                                this.loadRoute(path);
                            } else {
                                // Se cancelou, redirecionar para login
                                Notification.warning('É necessário fazer login para criar pedidos');
                                window.history.pushState({}, '', '/login');
                                this.loadRoute('/login');
                            }
                        });
                    return;
                } else {
                    // Se Auth não está disponível, redirecionar para login
                    Notification.warning('É necessário fazer login para criar pedidos');
                    window.history.pushState({}, '', '/login');
                    this.loadRoute('/login');
                    return;
                }
            }
        }
        
        window.history.pushState({}, '', path);
        this.loadRoute(path);
    },

    /**
     * Carrega rota
     */
    loadRoute(path) {
        // Normalizar path
        path = path === '' ? '/' : path;

        const route = this.routes[path];

        if (route) {
            this.currentRoute = path;
            this.updateActiveNav(path);
            route();
        } else {
            this.navigate('/painel');
        }
    },

    /**
     * Atualiza navegação ativa
     */
    updateActiveNav(path) {
        // Remove active de todos
        document.querySelectorAll('.nav-button').forEach(btn => {
            btn.classList.remove('active');
        });

        // Adiciona active no botão correto
        if (path === '/criar-pedido') {
            const btn = document.getElementById('nav-criar');
            if (btn) btn.classList.add('active');
        } else if (path === '/painel' || path === '/') {
            const btn = document.getElementById('nav-painel');
            if (btn) btn.classList.add('active');
        } else if (path === '/login') {
            const btn = document.getElementById('nav-login');
            if (btn) btn.classList.add('active');
        }
    },

    /**
     * Carrega conteúdo da página
     */
    async loadPage(page) {
        const app = document.getElementById('app');
        
        if (!app) {
            console.error('Elemento #app não encontrado');
            return;
        }

        try {
            console.log(`📄 Carregando página: ${page}`);
            // Mostrar loading
            Utils.showLoading();

            // Buscar HTML da página
            const url = `/pages/${page}.html`;
            console.log(`🔗 Buscando: ${url}`);
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`Erro ao carregar página: ${response.status} - ${response.statusText}`);
            }

            const html = await response.text();
            console.log(`✅ HTML recebido (${html.length} caracteres)`);
            app.innerHTML = html;

            // Executar função de inicialização da página
            this.initPage(page);

        } catch (error) {
            console.error('❌ Erro ao carregar página:', error);
            app.innerHTML = this.getErrorPage(error.message);
        } finally {
            Utils.hideLoading();
        }
    },

    /**
     * Inicializa página carregada
     */
    initPage(page) {
        switch (page) {
            case 'login':
                Router.initLoginPage();
                break;
            case 'criar-pedido':
                // Verificar autenticação antes de permitir criar pedido
                if (typeof Auth === 'undefined' || !Auth.isAuthenticated()) {
                    if (typeof Notification !== 'undefined') {
                        Notification.warning('É necessário fazer login para criar pedidos');
                    }
                    this.navigate('/login');
                    return;
                }
                if (typeof FormManager !== 'undefined') {
                    FormManager.init();
                }
                break;
            case 'painel':
                if (typeof PainelManager !== 'undefined') {
                    PainelManager.init();
                }
                // Atualizar indicadores de autenticação após carregar painel
                if (typeof App !== 'undefined' && App.updateAuthIndicator) {
                    setTimeout(() => App.updateAuthIndicator(), 100);
                }
                break;
        }

        // Scroll para o topo
        window.scrollTo(0, 0);
    },
    
    /**
     * Inicializa página de login
     */
    initLoginPage() {
        const form = document.getElementById('login-form');
        const btnLoginEdit = document.getElementById('btn-login-edit');
        const btnLoginView = document.getElementById('btn-login-view');
        const errorDiv = document.getElementById('login-error');
        const errorText = document.getElementById('login-error-text');
        
        // Carregar credenciais salvas
        const storedCreds = Auth.loadStoredCredentials();
        if (storedCreds) {
            const usernameInput = document.getElementById('login-username');
            if (usernameInput) {
                usernameInput.value = storedCreds.username || 'admin';
            }
        }
        
        // Handler do formulário
        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const username = document.getElementById('login-username').value.trim();
                const password = document.getElementById('login-password').value.trim();
                const remember = document.getElementById('login-remember').checked;
                
                if (!username || !password) {
                    errorDiv.classList.remove('hidden');
                    errorText.textContent = 'Por favor, preencha usuário e senha';
                    return;
                }
                
                // Mostrar loading
                btnLoginEdit.disabled = true;
                btnLoginEdit.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Entrando...';
                
                const result = await Auth.login(username, password, remember);
                
                if (result.success) {
                    Notification.success('Login realizado com sucesso!');
                    // Atualizar indicadores de autenticação imediatamente
                    if (typeof App !== 'undefined' && App.updateAuthIndicator) {
                        App.updateAuthIndicator();
                    }
                    setTimeout(() => {
                        Router.navigate('/painel');
                    }, 500);
                } else {
                    errorDiv.classList.remove('hidden');
                    errorText.textContent = result.error || 'Credenciais inválidas';
                    btnLoginEdit.disabled = false;
                    btnLoginEdit.innerHTML = '<i class="fas fa-sign-in-alt mr-2"></i> Entrar para Editar';
                }
            });
        }
        
        // Botão para continuar sem login
        if (btnLoginView) {
            btnLoginView.addEventListener('click', () => {
                Router.navigate('/painel');
            });
        }
    },

    /**
     * Retorna HTML de página de erro
     */
    getErrorPage(message) {
        return `
            <div class="flex items-center justify-center min-h-[50vh]">
                <div class="text-center">
                    <i class="fas fa-exclamation-triangle text-6xl text-yellow-500 mb-4"></i>
                    <h2 class="text-2xl font-bold text-gray-800 mb-2">Erro ao Carregar Página</h2>
                    <p class="text-gray-600 mb-6">${Utils.escapeHtml(message)}</p>
                    <button onclick="Router.navigate('/painel')" class="btn btn-primary">
                        <i class="fas fa-home"></i>
                        Voltar ao Painel
                    </button>
                </div>
            </div>
        `;
    },

    /**
     * Recarrega página atual
     */
    reload() {
        this.loadRoute(this.currentRoute || '/painel');
    }
};

// Inicializar router quando o DOM estiver pronto
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => Router.init());
} else {
    Router.init();
}

