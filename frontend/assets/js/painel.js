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
    ordenadoPorDistancia: false,
    calculandoDistancias: false,

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

        // Botão ordenar por distância
        const btnDistancia = document.getElementById('btn-ordenar-distancia');
        if (btnDistancia) {
            btnDistancia.addEventListener('click', () => this.ordenarPorDistancia());
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

        // Filtrar pedidos: concluídos só aparecem se o filtro "concluido" estiver ativo
        let pedidosParaExibir = [...this.pedidos];
        if (this.filtros.status !== 'concluido') {
            // Ocultar pedidos concluídos da lista principal
            pedidosParaExibir = pedidosParaExibir.filter(p => p.status !== 'concluido');
        }

        if (pedidosParaExibir.length === 0) {
            container.innerHTML = this.getEmptyState();
            return;
        }

        // Ordenar pedidos: mais próximos do dia atual primeiro
        const pedidosOrdenados = this.sortPedidosByProximity(pedidosParaExibir);

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

        // Ocultar pedidos concluídos da lista principal (exceto quando filtro "concluido" está ativo)
        if (this.filtros.status !== 'concluido') {
            filtered = filtered.filter(p => p.status !== 'concluido');
        }

        // Filtrar por status específico (se não for "todos")
        if (this.filtros.status && this.filtros.status !== 'concluido') {
            filtered = filtered.filter(p => p.status === this.filtros.status);
        } else if (this.filtros.status === 'concluido') {
            // Mostrar apenas concluídos
            filtered = this.pedidos.filter(p => p.status === 'concluido');
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
        
        // Filtrar pedidos concluídos (não devem ser ordenados por proximidade)
        const pedidosPendentes = pedidos.filter(p => p.status !== 'concluido');
        const pedidosConcluidos = pedidos.filter(p => p.status === 'concluido');
        
        // Ordenar apenas os pendentes por proximidade
        pedidosPendentes.sort((a, b) => {
            try {
                // Criar objetos Date para cada pedido
                const dateA = new Date(a.dia_entrega + 'T' + a.horario);
                const dateB = new Date(b.dia_entrega + 'T' + b.horario);
                
                // Calcular diferença em relação ao momento atual
                const diffA = Math.abs(dateA - now);
                const diffB = Math.abs(dateB - now);
                
                // Ordenar por proximidade (menor diferença primeiro)
                return diffA - diffB;
            } catch (error) {
                console.error('Erro ao ordenar pedidos:', error);
                return 0;
            }
        });
        
        // Retornar pendentes ordenados + concluídos no final (se houver)
        return [...pedidosPendentes, ...pedidosConcluidos];
    },

    /**
     * Ordena pedidos por distância da floricultura
     * Usa a API do OpenRouteService para calcular distâncias
     */
    async ordenarPorDistancia() {
        if (this.calculandoDistancias) {
            Notification.warning('Aguarde, calculando distâncias...');
            return;
        }

        const btnDistancia = document.getElementById('btn-ordenar-distancia');
        
        try {
            this.calculandoDistancias = true;
            
            // Atualizar botão para mostrar loading
            if (btnDistancia) {
                btnDistancia.innerHTML = '<i class="fas fa-spinner fa-spin"></i> <span class="hidden sm:inline">Calculando...</span>';
                btnDistancia.disabled = true;
            }

            Notification.info('Calculando distâncias... Isso pode levar alguns segundos.');

            // Chamar API para calcular distâncias em lote com timeout
            const timeoutPromise = new Promise((_, reject) => 
                setTimeout(() => reject(new Error('Timeout - tente novamente')), 60000)
            );
            
            const apiPromise = API.calcularDistanciasLote();
            const result = await Promise.race([apiPromise, timeoutPromise]);

            if (result && result.success) {
                const data = result.data;
                
                // Atualizar distâncias nos pedidos locais
                if (data.resultados && Array.isArray(data.resultados)) {
                    data.resultados.forEach(res => {
                        const pedido = this.pedidos.find(p => p.id === res.id);
                        if (pedido && res.distancia_km !== undefined) {
                            pedido.distancia_km = res.distancia_km;
                        }
                    });
                }

                // Ordenar pedidos por distância
                this.pedidos.sort((a, b) => {
                    // Pedidos sem distância vão para o final
                    if (a.distancia_km === null && b.distancia_km === null) return 0;
                    if (a.distancia_km === null || a.distancia_km === undefined) return 1;
                    if (b.distancia_km === null || b.distancia_km === undefined) return -1;
                    return a.distancia_km - b.distancia_km;
                });

                this.ordenadoPorDistancia = true;

                // Re-renderizar
                this.renderPedidos();

                // Mostrar resultado
                const calculados = data.calculados || 0;
                const doCache = data.do_cache || 0;
                const ignorados = data.ignorados || 0;
                const erros = data.erros || 0;
                
                let msg = `${calculados} calculadas, ${doCache} do cache`;
                if (ignorados > 0) msg += `, ${ignorados} ignorados`;
                if (erros > 0) msg += `, ${erros} com erro`;
                
                Notification.success(`Pedidos ordenados! ${msg}`);

                // Atualizar estilo do botão
                if (btnDistancia) {
                    btnDistancia.classList.remove('bg-blue-100', 'text-blue-700');
                    btnDistancia.classList.add('bg-blue-600', 'text-white');
                }
            } else {
                throw new Error(result?.error || 'Erro ao calcular distâncias');
            }

        } catch (error) {
            console.error('Erro ao ordenar por distância:', error);
            Notification.error(`Erro: ${error.message || 'Falha ao calcular distâncias'}`);
        } finally {
            this.calculandoDistancias = false;
            
            // Restaurar botão
            if (btnDistancia) {
                btnDistancia.innerHTML = '<i class="fas fa-route"></i> <span class="hidden sm:inline">Distância</span>';
                btnDistancia.disabled = false;
            }
        }
    },

    /**
     * Formata distância para exibição
     */
    formatarDistancia(distanciaKm) {
        if (distanciaKm === null || distanciaKm === undefined) {
            return null;
        }
        if (distanciaKm < 1) {
            return `${Math.round(distanciaKm * 1000)} m`;
        }
        return `${distanciaKm.toFixed(1)} km`;
    },

    /**
     * Retorna cor baseada na distância
     */
    getCorDistancia(distanciaKm) {
        if (distanciaKm === null || distanciaKm === undefined) {
            return 'gray';
        }
        if (distanciaKm <= 5) return 'green';   // Perto
        if (distanciaKm <= 15) return 'yellow'; // Médio
        return 'red';                           // Longe
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

