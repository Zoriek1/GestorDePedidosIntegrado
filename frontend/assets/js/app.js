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
     * Verifica por atualizações do Service Worker usando Workbox
     */
    checkForUpdates() {
        if ('serviceWorker' in navigator) {
            // Evitar múltiplos registros
            if (this._swRegistration) {
                return;
            }
            
            // Usar workbox-window se disponível (carregado via CDN no index.html)
            if (typeof workbox !== 'undefined' && workbox.Workbox) {
                const wb = new workbox.Workbox('/sw.js');
                
                // Detectar quando há uma atualização disponível
                wb.addEventListener('waiting', () => {
                    // Nova versão disponível - mostrar notificação
                    this.showUpdateNotification(wb);
                });
                
                // NÃO adicionar listener 'controlling' com reload automático
                // Isso causa loop infinito com "Update on reload" do Chrome DevTools
                // O reload será controlado pelo usuário via banner de atualização
                
                // Registrar o SW
                wb.register().then((registration) => {
                    this._swRegistration = registration;
                    console.log('✅ Service Worker registrado (Workbox)');
                    // Configurar UI de atualização
                    this.setupServiceWorkerUpdateUI(registration);
                }).catch(error => {
                    console.warn('Erro ao registrar Service Worker:', error);
                });
            } else {
                // Fallback: registro manual do SW (compatibilidade)
                navigator.serviceWorker.register('/sw.js')
                    .then(registration => {
                        this._swRegistration = registration;
                        console.log('✅ Service Worker registrado (fallback)');
                        
                        // NÃO usar setInterval para update - workbox-window já gerencia
                        // Configurar UI de atualização
                        this.setupServiceWorkerUpdateUI(registration);
                    })
                    .catch(error => {
                        console.warn('Erro ao registrar Service Worker:', error);
                    });
            }
        }
    },

    /**
     * Configura UI de atualização do Service Worker (isolada e reutilizável)
     * Detecta SW waiting/installed e mostra banner para atualização controlada pelo usuário
     */
    setupServiceWorkerUpdateUI(registration) {
        const RELOAD_GUARD_KEY = 'sw-reload-guard';
        
        // Guard: evitar múltiplos reloads na mesma sessão
        if (sessionStorage.getItem(RELOAD_GUARD_KEY)) {
            return; // Já recarregou nesta sessão
        }

        // Detectar SW waiting (já instalado, aguardando ativação)
        if (registration.waiting) {
            this.showUpdateBanner(registration);
            return;
        }

        // Escutar updatefound para detectar nova versão sendo instalada
        registration.addEventListener('updatefound', () => {
            const newWorker = registration.installing;
            if (newWorker) {
                newWorker.addEventListener('statechange', () => {
                    // Quando o novo SW está instalado e há um controller ativo
                    // significa que há uma atualização disponível
                    if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                        this.showUpdateBanner(registration);
                    }
                });
            }
        });
    },

    /**
     * Mostra banner de atualização com botão controlado pelo usuário
     */
    showUpdateBanner(registration) {
        // Evitar múltiplos banners
        if (document.getElementById('sw-update-banner')) {
            return;
        }

        const RELOAD_GUARD_KEY = 'sw-reload-guard';
        
        // Criar banner
        const banner = document.createElement('div');
        banner.id = 'sw-update-banner';
        banner.className = 'fixed bottom-4 right-4 bg-primary text-white p-4 rounded-lg shadow-xl z-50 max-w-sm';
        banner.innerHTML = `
            <div class="flex items-start space-x-3">
                <i class="fas fa-sync-alt text-xl mt-1"></i>
                <div class="flex-1">
                    <p class="font-semibold mb-1">Nova versão disponível!</p>
                    <p class="text-sm opacity-90 mb-3">Clique em "Atualizar agora" para aplicar as mudanças.</p>
                    <div class="flex gap-2">
                        <button id="sw-update-btn" class="px-4 py-2 bg-white text-primary rounded hover:bg-gray-100 font-medium transition">
                            Atualizar agora
                        </button>
                        <button id="sw-update-dismiss" class="px-4 py-2 bg-white bg-opacity-20 rounded hover:bg-opacity-30 transition">
                            Depois
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(banner);

        // Botão "Atualizar agora"
        document.getElementById('sw-update-btn').addEventListener('click', () => {
            // Enviar SKIP_WAITING ao SW waiting (não ao controller)
            const waitingWorker = registration.waiting;
            if (waitingWorker) {
                waitingWorker.postMessage({ type: 'SKIP_WAITING' });
            } else if (navigator.serviceWorker.controller) {
                // Fallback: tentar enviar ao controller se waiting não estiver disponível
                navigator.serviceWorker.controller.postMessage({ type: 'SKIP_WAITING' });
            }

            // Remover banner
            banner.remove();

            // Escutar controllerchange com guard para recarregar apenas uma vez
            if (!sessionStorage.getItem(RELOAD_GUARD_KEY)) {
                navigator.serviceWorker.addEventListener('controllerchange', () => {
                    // Marcar guard antes de recarregar
                    sessionStorage.setItem(RELOAD_GUARD_KEY, 'true');
                    window.location.reload();
                }, { once: true });
            }
        });

        // Botão "Depois"
        document.getElementById('sw-update-dismiss').addEventListener('click', () => {
            banner.remove();
        });

        // Auto-remover após 30 segundos
        setTimeout(() => {
            if (banner.parentElement) {
                banner.remove();
            }
        }, 30000);
    },

    /**
     * Mostra notificação de atualização disponível com botão para atualizar (Workbox)
     * Mantida para compatibilidade com workbox-window, mas agora usa a função isolada
     */
    showUpdateNotification(wb) {
        // Usar a função isolada setupServiceWorkerUpdateUI se tiver registration
        if (this._swRegistration) {
            this.setupServiceWorkerUpdateUI(this._swRegistration);
        } else {
            // Fallback: usar workbox-window messageSW
            const RELOAD_GUARD_KEY = 'sw-reload-guard';
            if (sessionStorage.getItem(RELOAD_GUARD_KEY)) {
                return;
            }

            if (document.getElementById('sw-update-banner')) {
                return;
            }

            const banner = document.createElement('div');
            banner.id = 'sw-update-banner';
            banner.className = 'fixed bottom-4 right-4 bg-primary text-white p-4 rounded-lg shadow-xl z-50 max-w-sm';
            banner.innerHTML = `
                <div class="flex items-start space-x-3">
                    <i class="fas fa-sync-alt text-xl mt-1"></i>
                    <div class="flex-1">
                        <p class="font-semibold mb-1">Nova versão disponível!</p>
                        <p class="text-sm opacity-90 mb-3">Clique em "Atualizar agora" para aplicar as mudanças.</p>
                        <div class="flex gap-2">
                            <button id="sw-update-btn-wb" class="px-4 py-2 bg-white text-primary rounded hover:bg-gray-100 font-medium transition">
                                Atualizar agora
                            </button>
                            <button id="sw-update-dismiss-wb" class="px-4 py-2 bg-white bg-opacity-20 rounded hover:bg-opacity-30 transition">
                                Depois
                            </button>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.appendChild(banner);

            document.getElementById('sw-update-btn-wb').addEventListener('click', () => {
                if (wb && wb.messageSW) {
                    wb.messageSW({ type: 'SKIP_WAITING' });
                }

                banner.remove();

                if (!sessionStorage.getItem(RELOAD_GUARD_KEY)) {
                    navigator.serviceWorker.addEventListener('controllerchange', () => {
                        sessionStorage.setItem(RELOAD_GUARD_KEY, 'true');
                        window.location.reload();
                    }, { once: true });
                }
            });

            document.getElementById('sw-update-dismiss-wb').addEventListener('click', () => {
                banner.remove();
            });

            setTimeout(() => {
                if (banner.parentElement) {
                    banner.remove();
                }
            }, 30000);
        }
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

