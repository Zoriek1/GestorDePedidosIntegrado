/**
 * Plante Uma Flor - PWA v3.0
 * Aplicação Principal
 */

const App = {
    version: '3.0.1',
    initialized: false,
    _swRegistration: null, // Cache do registro do Service Worker

    /**
     * Inicializa a aplicação
     */
    async init() {
        if (this.initialized) {
            console.warn('App já inicializado');
            return;
        }

        try {
            // Inicializar IndexedDB
            await DB.init();

            // Configurar listeners globais (crítico - fazer primeiro)
            this.setupGlobalListeners();
            
            // Atualizar indicador de autenticação (crítico)
            this.updateAuthIndicator();
            
            // Atualizar apenas quando a visibilidade da página mudar (usuário volta à aba)
            document.addEventListener('visibilitychange', () => {
                if (!document.hidden) {
                    this.updateAuthIndicator();
                }
            });

            this.initialized = true;

            // Operações não críticas - adiar para não bloquear inicialização
            // Verificar conectividade de forma assíncrona
            setTimeout(() => {
                this.checkConnectivity();
            }, 100);

            // Verificar por atualizações do Service Worker (adiar)
            setTimeout(() => {
                this.checkForUpdates();
            }, 2000);

            // Prompt de instalação PWA (adiar)
            setTimeout(() => {
                this.setupInstallPrompt();
            }, 2000);

            // Mostrar notificação de boas-vindas
            setTimeout(() => {
                if (!sessionStorage.getItem('welcomed')) {
                    Notification.success('Bem-vindo ao Plante Uma Flor! 🌺');
                    sessionStorage.setItem('welcomed', 'true');
                }
            }, 1000);

        } catch (error) {
            console.error('❌ Erro ao inicializar aplicação:', error);
            Notification.error('Erro ao inicializar aplicação');
        }
    },

    /**
     * Atualiza indicador de autenticação e controles de navegação
     */
    updateAuthIndicator() {
        const indicator = document.getElementById('auth-indicator');
        const btnLogout = document.getElementById('btn-logout');
        const btnLogin = document.getElementById('nav-login');
        const btnCriarPedido = document.getElementById('nav-criar');
        const btnCriarPedidoPainel = document.getElementById('btn-novo-pedido-painel');
        
        // Cachear resultado para evitar múltiplas chamadas na mesma execução
        const isAuthenticated = typeof Auth !== 'undefined' && Auth.isAuthenticated();
        
        // Usar classes CSS ao invés de múltiplas manipulações de estilo
        if (indicator) {
            indicator.classList.toggle('hidden', !isAuthenticated);
            indicator.classList.toggle('flex', isAuthenticated);
        }
        
        if (btnLogout) {
            btnLogout.classList.toggle('hidden', !isAuthenticated);
        }
        
        if (btnLogin) {
            btnLogin.classList.toggle('hidden', isAuthenticated);
            btnLogin.classList.toggle('auth-hidden', isAuthenticated);
        }
        
        if (btnCriarPedido) {
            btnCriarPedido.classList.toggle('hidden', !isAuthenticated);
        }
        
        if (btnCriarPedidoPainel) {
            btnCriarPedidoPainel.classList.toggle('hidden', !isAuthenticated);
        }
    },
    
    /**
     * Verifica conectividade e sincroniza dados
     */
    async checkConnectivity() {
        if (Utils.isOnline()) {
            try {
                // Sincronizar pedidos pendentes do IndexedDB
                await DB.syncPendingPedidos();
                
                // Verificar health do servidor
                await API.healthCheck();
            } catch (error) {
                // Silencioso - não precisa logar erros de conectividade
            }
        } else {
            Notification.warning('Você está offline. As alterações serão sincronizadas quando voltar online.');
        }
    },

    
    /**
     * Configura listeners globais
     */
    setupGlobalListeners() {
        // Online/Offline events
        window.addEventListener('online', () => {
            this.checkConnectivity();
        });

        window.addEventListener('offline', () => {
            // Silencioso
        });

        // Antes de sair da página
        window.addEventListener('beforeunload', (e) => {
            // Verificar se há pedidos pendentes
            DB.getPendingPedidos().then(pending => {
                if (pending.length > 0) {
                    e.preventDefault();
                    e.returnValue = 'Você tem pedidos pendentes de sincronização. Tem certeza que deseja sair?';
                }
            });
        });

        // Atalhos de teclado
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + K: Buscar
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                const searchInput = document.getElementById('search-input');
                if (searchInput) {
                    searchInput.focus();
                }
            }

            // Ctrl/Cmd + N: Novo pedido
            if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
                e.preventDefault();
                Router.navigate('/criar-pedido');
            }

            // Ctrl/Cmd + H: Home/Painel
            if ((e.ctrlKey || e.metaKey) && e.key === 'h') {
                e.preventDefault();
                Router.navigate('/painel');
            }
        });

        // Visibilidade da página
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                // Recarregar dados se estiver no painel
                if (Router.currentRoute === '/painel' && typeof PainelManager !== 'undefined') {
                    PainelManager.loadPedidos();
                }
            }
        });
        
    },

    /**
     * Verifica por atualizações do Service Worker e força atualização automática
     */
    checkForUpdates() {
        if (!('serviceWorker' in navigator)) return;
        if (this._swRegistration) return;

        // Escutar controllerchange ANTES de registrar (reload automático)
        let refreshing = false;
        navigator.serviceWorker.addEventListener('controllerchange', () => {
            if (refreshing) return;
            refreshing = true;
            window.location.reload();
        });

        navigator.serviceWorker.register('/sw.js')
            .then(registration => {
                this._swRegistration = registration;
                console.log('✅ Service Worker registrado');

                // Checar atualização imediatamente
                registration.update();

                // Se já tem SW waiting, enviar SKIP_WAITING
                if (registration.waiting) {
                    registration.waiting.postMessage({ type: 'SKIP_WAITING' });
                }

                // Detectar novo SW instalando
                registration.addEventListener('updatefound', () => {
                    const newWorker = registration.installing;
                    if (!newWorker) return;

                    newWorker.addEventListener('statechange', () => {
                        if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                            // Enviar SKIP_WAITING automaticamente
                            newWorker.postMessage({ type: 'SKIP_WAITING' });
                        }
                    });
                });
            })
            .catch(error => console.warn('Erro ao registrar Service Worker:', error));
    },


    /**
     * Configura prompt de instalação PWA
     */
    setupInstallPrompt() {
        let deferredPrompt;

        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            deferredPrompt = e;

            // Verificar se já foi instalado ou prompt foi mostrado
            if (!localStorage.getItem('pwa-install-prompt-shown')) {
                this.showInstallBanner(deferredPrompt);
            }
        });

        // Detectar quando app é instalado
        window.addEventListener('appinstalled', () => {
            Notification.success('App instalado com sucesso! 🎉');
            deferredPrompt = null;
        });
    },

    /**
     * Mostra banner de instalação
     */
    showInstallBanner(deferredPrompt) {
        const banner = document.createElement('div');
        banner.className = 'fixed bottom-20 left-4 right-4 bg-primary text-white p-4 rounded-lg shadow-xl z-50 animate-fade-in';
        banner.innerHTML = `
            <div class="flex items-center justify-between">
                <div class="flex-1">
                    <p class="font-semibold">Instalar Plante Uma Flor</p>
                    <p class="text-sm opacity-90">Adicione à tela inicial para acesso rápido</p>
                </div>
                <div class="flex gap-2 ml-4">
                    <button id="install-dismiss" class="px-3 py-1 bg-white bg-opacity-20 rounded hover:bg-opacity-30 transition">
                        Depois
                    </button>
                    <button id="install-app" class="px-3 py-1 bg-white text-primary rounded hover:bg-gray-100 transition">
                        Instalar
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(banner);

        // Botão Instalar
        document.getElementById('install-app').addEventListener('click', async () => {
            if (deferredPrompt) {
                deferredPrompt.prompt();
                await deferredPrompt.userChoice;
                
                localStorage.setItem('pwa-install-prompt-shown', 'true');
                banner.remove();
            }
        });

        // Botão Depois
        document.getElementById('install-dismiss').addEventListener('click', () => {
            banner.remove();
            localStorage.setItem('pwa-install-prompt-shown', 'true');
        });

        // Auto-remover após 10 segundos
        setTimeout(() => {
            if (banner.parentElement) {
                banner.remove();
            }
        }, 10000);
    },

    /**
     * Limpa cache e dados locais
     */
    async clearAllData() {
        const confirmed = await Modal.confirm({
            title: 'Limpar Todos os Dados',
            message: 'Isso vai limpar o cache e dados locais. Tem certeza?',
            confirmText: 'Limpar',
            cancelText: 'Cancelar'
        });

        if (confirmed) {
            try {
                // Limpar IndexedDB
                await DB.clearAll();

                // Limpar Cache do Service Worker
                if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
                    navigator.serviceWorker.controller.postMessage({
                        type: 'CLEAR_CACHES'
                    });
                }

                // Limpar Storage
                localStorage.clear();
                sessionStorage.clear();

                Notification.success('Dados limpos com sucesso!');
                
                // Recarregar após 1 segundo
                setTimeout(() => {
                    window.location.reload();
                }, 1000);

            } catch (error) {
                console.error('Erro ao limpar dados:', error);
                Notification.error('Erro ao limpar dados');
            }
        }
    }
};

// Inicializar quando o DOM estiver pronto
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => App.init());
} else {
    App.init();
}

// Expor App globalmente para debug
window.App = App;

