/**
 * Plante Uma Flor - PWA v3.0
 * Painel Manager - Gerenciador do painel de pedidos
 */

const PainelManager = {
    pedidos: [],
    filtros: {
        status: '',
        search: ''
    },
    autoRefreshInterval: null,
    autoRefreshTime: 30000, // 30 segundos

    /**
     * Inicializa o painel
     */
    async init() {
        console.log('📊 Inicializando painel');

        // Configurar listeners
        this.setupListeners();

        // Carregar pedidos e renderizar somente após dados prontos
        await this.refreshPedidos();

        // Carregar estatísticas (não precisa bloquear o init)
        this.loadStats();

        // Configurar auto-refresh
        this.setupAutoRefresh();
    },

    /**
     * Configura event listeners
     */
   setupListeners() {
        // Busca
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.addEventListener('input', Utils.debounce((e) => {
                this.filtros.search = e.target.value;
                this.filterPedidos();
            }, 300));
        }

        // Filtros de status
        document.querySelectorAll('[data-filter-status]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const status = e.currentTarget.getAttribute('data-filter-status');
                this.setStatusFilter(status);
            });
        });

        // Botão atualizar
        const btnRefresh = document.getElementById('btn-refresh');
        if (btnRefresh) {
            btnRefresh.addEventListener('click', () => this.refreshPedidos(true));
        }

        // Botão limpar antigos
        const btnCleanup = document.getElementById('btn-cleanup');
        if (btnCleanup) {
            btnCleanup.addEventListener('click', () => this.cleanupOldPedidos());
        }
    },

    /**
     * Carrega pedidos da API
     */
     async refreshPedidos(showNotification = false) {
        try {
            if (showNotification) Utils.showLoading();

            this.pedidos = await this.fetchPedidos();

            this.renderPedidos();

            if (showNotification) Notification.success('Pedidos atualizados!');
        } catch (error) {
            console.error('Erro ao atualizar pedidos:', error);
            Notification.error('Erro ao atualizar pedidos');
        } finally {
            if (showNotification) Utils.hideLoading();
        }
    },

    // Compatibilidade: manter antiga assinatura
    loadPedidos(showNotification = false) {
        return this.refreshPedidos(showNotification);
    },

    // 📦 Busca pedidos (API → cache → fallback)
    async fetchPedidos() {
        try {
            if (Utils.isOnline()) {
                const result = await API.getPedidos(this.filtros);

                if (result.success) {
                    await DB.cachePedidos(result.data.pedidos);
                    return result.data.pedidos;
                }

                console.warn('⚠️ Falha na API, carregando do cache...');
            }

            // fallback offline
            const cached = await DB.getCachedPedidos();
            Notification.warning('Mostrando dados em cache (offline)');
            return cached;
        } catch (error) {
            console.error('Erro ao buscar pedidos:', error);
            return await DB.getCachedPedidos();
        }
    },

    /**
     * Carrega estatísticas
     */
    async loadStats() {
        try {
            const result = await API.getStats();

            if (result.success) {
                this.renderStats(result.data.stats);
            }
        } catch (error) {
            console.error('Erro ao carregar estatísticas:', error);
        }
    },

    /**
     * Renderiza estatísticas
     */
    renderStats(stats) {
        // Atualizar contadores
        document.getElementById('stat-total')?.setAttribute('data-count', stats.total || 0);
        document.getElementById('stat-agendado')?.setAttribute('data-count', stats.agendado || 0);
        document.getElementById('stat-producao')?.setAttribute('data-count', stats.em_producao || 0);
        document.getElementById('stat-pronto')?.setAttribute('data-count', (stats.pronto_entrega || 0) + (stats.pronto_retirada || 0));
        
        // Animar números
        this.animateNumbers();
    },

    /**
     * Anima contadores
     */
    animateNumbers() {
        document.querySelectorAll('[data-count]').forEach(element => {
            const target = parseInt(element.getAttribute('data-count'));
            const duration = 1000;
            const step = target / (duration / 16);
            let current = 0;

            const timer = setInterval(() => {
                current += step;
                if (current >= target) {
                    element.textContent = target;
                    clearInterval(timer);
                } else {
                    element.textContent = Math.floor(current);
                }
            }, 16);
        });
    },

    /**
     * Renderiza lista de pedidos
     */
    renderPedidos() {
        const container = document.getElementById('pedidos-container');
        
        if (!container) {
            console.warn('Container de pedidos não encontrado');
            return;
        }

        // Limpar container
        container.innerHTML = '';

        if (this.pedidos.length === 0) {
            container.innerHTML = this.getEmptyState();
            return;
        }

        // Ordenar pedidos: mais próximos do dia atual primeiro
        const pedidosOrdenados = this.sortPedidosByProximity([...this.pedidos]);

        // Criar cards
        pedidosOrdenados.forEach(pedido => {
            const card = PedidoCard.create(pedido);
            container.appendChild(card);
        });

        console.log(`✅ ${pedidosOrdenados.length} pedidos renderizados (ordenados por proximidade)`);
    },

    /**
     * Retorna HTML do estado vazio
     */
    getEmptyState() {
        const message = this.filtros.status || this.filtros.search
            ? 'Nenhum pedido encontrado com os filtros aplicados'
            : 'Nenhum pedido cadastrado ainda';

        return `
            <div class="flex flex-col items-center justify-center py-16 text-center">
                <i class="fas fa-inbox text-6xl text-gray-300 mb-4"></i>
                <h3 class="text-xl font-semibold text-gray-600 mb-2">${message}</h3>
                <p class="text-gray-500 mb-6">
                    ${this.filtros.status || this.filtros.search 
                        ? 'Tente ajustar os filtros ou fazer uma nova busca' 
                        : 'Crie seu primeiro pedido clicando no botão acima'}
                </p>
                <button onclick="Router.navigate('/criar-pedido')" class="btn btn-primary">
                    <i class="fas fa-plus-circle"></i>
                    Criar Primeiro Pedido
                </button>
            </div>
        `;
    },

    /**
     * Filtra pedidos localmente
     */
    filterPedidos() {
        let filtered = [...this.pedidos];

        // Filtrar por status
        if (this.filtros.status) {
            filtered = filtered.filter(p => p.status === this.filtros.status);
        }

        // Filtrar por busca
        if (this.filtros.search) {
            const search = this.filtros.search.toLowerCase();
            filtered = filtered.filter(p => 
                (p.cliente && p.cliente.toLowerCase().includes(search)) ||
                (p.destinatario && p.destinatario.toLowerCase().includes(search)) ||
                (p.produto && p.produto.toLowerCase().includes(search)) ||
                (p.telefone_cliente && p.telefone_cliente.includes(search))
            );
        }

        // Ordenar pedidos filtrados por proximidade
        filtered = this.sortPedidosByProximity(filtered);

        // Renderizar filtrados
        const container = document.getElementById('pedidos-container');
        if (container) {
            container.innerHTML = '';
            
            if (filtered.length === 0) {
                container.innerHTML = this.getEmptyState();
            } else {
                filtered.forEach(pedido => {
                    const card = PedidoCard.create(pedido);
                    container.appendChild(card);
                });
            }
        }
    },

    /**
     * Define filtro de status
     */
    setStatusFilter(status) {
        this.filtros.status = status === 'todos' ? '' : status;
        
        // Atualizar botões ativos
        document.querySelectorAll('[data-filter-status]').forEach(btn => {
            btn.classList.remove('active', 'bg-primary', 'text-white');
            btn.classList.add('bg-gray-200', 'text-gray-700');
        });

        const activeBtn = document.querySelector(`[data-filter-status="${status || 'todos'}"]`);
        if (activeBtn) {
            activeBtn.classList.remove('bg-gray-200', 'text-gray-700');
            activeBtn.classList.add('active', 'bg-primary', 'text-white');
        }

        // Aplicar filtro
        this.filterPedidos();
    },

    /**
     * Muda status de um pedido
     */
    async changeStatus(pedidoId, novoStatus) {
        if (!novoStatus) return;

        try {
            const result = await API.updatePedidoStatus(pedidoId, novoStatus);

            if (result.success) {
                // Atualizar pedido local
                const pedido = this.pedidos.find(p => p.id === pedidoId);
                if (pedido) {
                    pedido.status = novoStatus;
                }

                // Re-renderizar
                this.renderPedidos();

                Notification.success('Status atualizado!');
                
                // Recarregar estatísticas
                this.loadStats();
            } else {
                throw new Error(result.error);
            }

        } catch (error) {
            console.error('Erro ao atualizar status:', error);
            Notification.error('Erro ao atualizar status');
            
            // Reverter select
            const select = document.querySelector(`[data-id="${pedidoId}"] select`);
            if (select) {
                const pedido = this.pedidos.find(p => p.id === pedidoId);
                if (pedido) {
                    select.value = pedido.status;
                }
            }
        }
    },

    /**
     * Deleta um pedido
     */
    async deletePedido(pedidoId) {
        const confirmed = await Modal.confirmDelete('este pedido');

        if (!confirmed) return;

        try {
            Utils.showLoading();

            const result = await API.deletePedido(pedidoId);

            if (result.success) {
                // Remover pedido local
                this.pedidos = this.pedidos.filter(p => p.id !== pedidoId);

                // Re-renderizar
                this.renderPedidos();

                Notification.success('Pedido deletado com sucesso!');
                
                // Recarregar estatísticas
                this.loadStats();
            } else {
                throw new Error(result.error);
            }

        } catch (error) {
            console.error('Erro ao deletar pedido:', error);
            Notification.error('Erro ao deletar pedido');
        } finally {
            Utils.hideLoading();
        }
    },

    /**
     * Ordena pedidos por proximidade da data atual
     * Pedidos mais próximos aparecem primeiro
     */
    sortPedidosByProximity(pedidos) {
        const now = new Date();
        
        return pedidos.sort((a, b) => {
            try {
                // Criar objetos Date para cada pedido
                const dateA = new Date(a.dia_entrega + 'T' + a.horario);
                const dateB = new Date(b.dia_entrega + 'T' + b.horario);
                
                // Calcular diferença em relação ao momento atual
                const diffA = Math.abs(dateA - now);
                const diffB = Math.abs(dateB - now);
                
                // Priorizar pedidos não concluídos
                if (a.status === 'concluido' && b.status !== 'concluido') return 1;
                if (a.status !== 'concluido' && b.status === 'concluido') return -1;
                
                // Ordenar por proximidade (menor diferença primeiro)
                return diffA - diffB;
            } catch (error) {
                console.error('Erro ao ordenar pedidos:', error);
                return 0;
            }
        });
    },

    /**
     * Limpa pedidos antigos
     */
    async cleanupOldPedidos() {
        const confirmed = await Modal.confirm({
            title: 'Arquivar Pedidos Antigos',
            message: 'Isso vai arquivar (ocultar) pedidos concluídos há mais de 1 dia da lista. Os dados permanecerão no banco de dados. Deseja continuar?',
            confirmText: 'Arquivar',
            cancelText: 'Cancelar',
            icon: 'fa-broom'
        });

        if (!confirmed) return;

        try {
            Utils.showLoading();

            const result = await API.cleanupOldPedidos(1);

            if (result.success) {
                Notification.success(`${result.data.count} pedidos arquivados (ocultos da lista)`);
                
                // Recarregar lista
                await this.loadPedidos();
            } else {
                throw new Error(result.error || 'Falha ao arquivar');
            }

        } catch (error) {
            console.error('Erro ao arquivar pedidos:', error);
            Notification.error(`Erro ao arquivar pedidos antigos: ${error.message || ''}`.trim());
        } finally {
            Utils.hideLoading();
        }
    },

    /**
     * Configura auto-refresh
     */
    setupAutoRefresh() {
        // Limpar intervalo existente
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }

        // Configurar novo intervalo
        this.autoRefreshInterval = setInterval(() => {
            if (document.hidden) return; // Não atualizar se página não está visível
            
            console.log('🔄 Auto-refresh disparado');
            this.loadPedidos(false);
            this.loadStats();
        }, this.autoRefreshTime);

        console.log(`✅ Auto-refresh configurado (${this.autoRefreshTime / 1000}s)`);
    },

    /**
     * Para auto-refresh
     */
    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
            console.log('⏸️ Auto-refresh parado');
        }
    },

    /**
     * Limpa recursos ao sair do painel
     */
    cleanup() {
        this.stopAutoRefresh();
    }
};

// Parar auto-refresh ao navegar para outra página
window.addEventListener('beforeunload', () => {
    if (typeof PainelManager !== 'undefined') {
        PainelManager.cleanup();
    }
});

