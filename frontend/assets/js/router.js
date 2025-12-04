/**
 * Plante Uma Flor - PWA v3.0
 * Client-Side Router - Navegação SPA
 */

const Router = {
    routes: {
        '/': () => Router.navigate('/painel'),
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
            // Mostrar loading
            Utils.showLoading();

            // Buscar HTML da página
            const response = await fetch(`/pages/${page}.html`);
            
            if (!response.ok) {
                throw new Error(`Erro ao carregar página: ${response.status}`);
            }

            const html = await response.text();
            app.innerHTML = html;

            // Executar função de inicialização da página
            this.initPage(page);

        } catch (error) {
            console.error('Erro ao carregar página:', error);
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
            case 'criar-pedido':
                if (typeof FormManager !== 'undefined') {
                    FormManager.init();
                }
                break;
            case 'painel':
                if (typeof PainelManager !== 'undefined') {
                    PainelManager.init();
                }
                break;
        }

        // Scroll para o topo
        window.scrollTo(0, 0);
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

