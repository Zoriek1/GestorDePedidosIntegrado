/**
 * Plante Uma Flor - PWA v3.0
 * Painel Manager - Gerenciador do painel de pedidos
 */

const PainelManager = {
    pedidos: [],
    pedidosAnteriores: [], // Armazenar lista anterior para detectar novos
    filtros: {
        status: '',
        search: '',
        date: 'todos'  // todos, hoje, amanha, semana
    },
    autoRefreshInterval: null,
    autoRefreshTime: 30000, // 30 segundos (otimizado para melhor performance)
    ordenadoPorDistancia: false,
    calculandoDistancias: false,
    modoSelecao: false,
    pedidosSelecionados: new Set(),

    /**
     * Inicializa o painel
     */
    async init() {

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

        // Filtros de data
        document.querySelectorAll('[data-filter-date]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const date = e.currentTarget.getAttribute('data-filter-date');
                this.setDateFilter(date);
            });
        });

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

        const btnRotaOtimizada = document.getElementById('btn-rota-otimizada');
        if (btnRotaOtimizada) {
            btnRotaOtimizada.addEventListener('click', () => this.calcularRotaOtimizada());
        }

        // Botão exportar planilha
        const btnExportarPlanilha = document.getElementById('btn-exportar-planilha');
        if (btnExportarPlanilha) {
            btnExportarPlanilha.addEventListener('click', () => this.exportarPlanilha());
        }
    },

    /**
     * Exporta vendas para Google Sheets
     */
    async exportarPlanilha() {
        try {
            const confirmou = await Modal.confirm(
                'Exportar para Planilha',
                'Deseja atualizar a planilha do Google Sheets com as vendas do mês atual?',
                'Exportar',
                'Cancelar'
            );

            if (!confirmou) return;

            Utils.showLoading('Exportando para Google Sheets...');

            const response = await API.post('/api/exportar-planilha', {});

            Utils.hideLoading();

            if (response.success) {
                Notification.success('Planilha atualizada com sucesso!');
            } else {
                Notification.error(response.error || 'Erro ao exportar');
            }
        } catch (error) {
            Utils.hideLoading();
            console.error('Erro ao exportar:', error);
            Notification.error('Erro ao exportar. Verifique se as credenciais do Google estão configuradas.');
        }
    },

    /**
     * Carrega pedidos da API
     */
    async refreshPedidos(showNotification = false) {
        try {
            if (showNotification) Utils.showLoading();

            // Salvar lista anterior para detectar novos pedidos
            const pedidosAnteriores = [...this.pedidos];

            // Buscar novos pedidos
            const novosPedidos = await this.fetchPedidos();

            // Detectar pedidos novos (que não estavam na lista anterior)
            const idsAnteriores = new Set(pedidosAnteriores.map(p => p.id));
            const pedidosNovos = novosPedidos.filter(p => !idsAnteriores.has(p.id));

            // Marcar pedidos novos
            novosPedidos.forEach(pedido => {
                pedido.novo = pedidosNovos.some(novo => novo.id === pedido.id);
            });

            // Atualizar lista
            this.pedidosAnteriores = pedidosAnteriores;
            this.pedidos = novosPedidos;

            // Sempre manter filtros ativos - aplicar filtros se houver algum ativo
            // Isso garante que os filtros sejam persistentes mesmo após auto-refresh
            const temFiltrosAtivos = this.filtros.date !== 'todos' || this.filtros.status || this.filtros.search;

            if (temFiltrosAtivos) {
                // Aplicar filtros mantendo o estado
                this.filterPedidos();
            } else {
                // Sem filtros - renderizar normalmente
                this.renderPedidos();
            }

            // Garantir que botões de filtro mantenham estado visual
            this.updateFilterButtons();

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
                
                // Log para debug
                console.log('[DEBUG] Resultado da API:', {
                    success: result.success,
                    hasData: !!result.data,
                    dataKeys: result.data ? Object.keys(result.data) : [],
                    pedidosCount: result.data?.pedidos?.length ?? 'undefined'
                });

                if (result.success && result.data) {
                    // Validar se pedidos existe e é array
                    const pedidos = result.data.pedidos;
                    
                    if (Array.isArray(pedidos)) {
                        await DB.cachePedidos(pedidos);
                        return pedidos;
                    } else {
                        console.error('[ERRO] result.data.pedidos não é um array:', pedidos);
                        // Fallback para cache
                    }
                } else {
                    console.warn('⚠️ Falha na API, carregando do cache...');
                }
            }

            // fallback offline
            const cached = await DB.getCachedPedidos();
            if (cached && cached.length > 0) {
                Notification.warning('Mostrando dados em cache (offline)');
            }
            return cached || [];
        } catch (error) {
            console.error('Erro ao buscar pedidos:', error);
            return await DB.getCachedPedidos() || [];
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
    renderPedidos(forceAnimation = false) {
        const container = document.getElementById('pedidos-container');

        if (!container) {
            console.warn('Container de pedidos não encontrado');
            return;
        }

        // Se não for forçar animação, fazer update inteligente (não recriar tudo)
        if (!forceAnimation && container.children.length > 0) {
            // Atualizar apenas pedidos existentes e adicionar novos
            this.updatePedidosInteligente();
            this.updateFilterButtons();
            return;
        }

        // Limpar container apenas se forçar animação ou primeira renderização
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
            const card = PedidoCard.create(pedido, this.modoSelecao, this.pedidosSelecionados.has(pedido.id));
            // Aplicar animação apenas se for pedido novo
            if (!pedido.novo) {
                card.classList.add('no-animation');
            }
            container.appendChild(card);
        });

        // Garantir que os botões de filtro permaneçam com estilo correto
        this.updateFilterButtons();
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
     * Atualiza pedidos de forma inteligente (sem recriar tudo)
     */
    updatePedidosInteligente() {
        const container = document.getElementById('pedidos-container');
        if (!container) return;

        // Obter IDs dos pedidos atualmente exibidos
        const idsExibidos = new Set(
            Array.from(container.children).map(card => parseInt(card.dataset.id))
        );

        // Filtrar pedidos: concluídos só aparecem se o filtro "concluido" estiver ativo
        let pedidosParaExibir = [...this.pedidos];
        if (this.filtros.status !== 'concluido') {
            pedidosParaExibir = pedidosParaExibir.filter(p => p.status !== 'concluido');
        }

        // Aplicar filtros de data e busca
        if (this.filtros.date && this.filtros.date !== 'todos') {
            const hoje = new Date();
            const hojeStr = hoje.toISOString().split('T')[0];
            const amanha = new Date(hoje);
            amanha.setDate(amanha.getDate() + 1);
            const amanhaStr = amanha.toISOString().split('T')[0];
            const fimSemana = new Date(hoje);
            fimSemana.setDate(fimSemana.getDate() + 7);
            const fimSemanaStr = fimSemana.toISOString().split('T')[0];

            pedidosParaExibir = pedidosParaExibir.filter(p => {
                const dataEntregaStr = p.dia_entrega;
                if (this.filtros.date === 'hoje') return dataEntregaStr === hojeStr;
                if (this.filtros.date === 'amanha') return dataEntregaStr === amanhaStr;
                if (this.filtros.date === 'semana') return dataEntregaStr >= hojeStr && dataEntregaStr <= fimSemanaStr;
                return true;
            });
        }

        if (this.filtros.status && this.filtros.status !== 'concluido') {
            pedidosParaExibir = pedidosParaExibir.filter(p => p.status === this.filtros.status);
        } else if (this.filtros.status === 'concluido') {
            pedidosParaExibir = this.pedidos.filter(p => p.status === 'concluido');
        }

        if (this.filtros.search) {
            const search = this.filtros.search.toLowerCase();
            pedidosParaExibir = pedidosParaExibir.filter(p =>
                (p.cliente && p.cliente.toLowerCase().includes(search)) ||
                (p.destinatario && p.destinatario.toLowerCase().includes(search)) ||
                (p.produto && p.produto.toLowerCase().includes(search)) ||
                (p.telefone_cliente && p.telefone_cliente.includes(search))
            );
        }

        // Ordenar
        pedidosParaExibir = this.sortPedidosByProximity(pedidosParaExibir);

        const idsParaExibir = new Set(pedidosParaExibir.map(p => p.id));

        // Remover cards de pedidos que não devem mais aparecer
        Array.from(container.children).forEach(card => {
            const pedidoId = parseInt(card.dataset.id);
            if (!idsParaExibir.has(pedidoId)) {
                card.remove();
            }
        });

        // Atualizar ou adicionar cards mantendo ordem
        pedidosParaExibir.forEach((pedido, index) => {
            const cardExistente = container.querySelector(`[data-id="${pedido.id}"]`);

            if (cardExistente) {
                // Atualizar card existente sem recriar (apenas atualizar dados se necessário)
                // Verificar se precisa atualizar (status mudou, etc)
                const statusAtual = cardExistente.dataset.status;
                if (statusAtual !== pedido.status) {
                    // Status mudou - atualizar card
                    const novoCard = PedidoCard.create(pedido, this.modoSelecao, this.pedidosSelecionados.has(pedido.id));
                    novoCard.classList.add('no-animation');
                    cardExistente.replaceWith(novoCard);
                }
                // Se não mudou nada, manter o card como está (sem animação)
            } else {
                // Adicionar novo card na posição correta
                const novoCard = PedidoCard.create(pedido, this.modoSelecao, this.pedidosSelecionados.has(pedido.id));
                // Aplicar animação apenas se for pedido novo
                if (!pedido.novo) {
                    novoCard.classList.add('no-animation');
                }

                // Inserir na posição correta baseada na ordem
                const proximoCard = Array.from(container.children).find(card => {
                    const cardId = parseInt(card.dataset.id);
                    const proximoPedido = pedidosParaExibir[index + 1];
                    return proximoPedido && cardId === proximoPedido.id;
                });

                if (proximoCard) {
                    container.insertBefore(novoCard, proximoCard);
                } else {
                    container.appendChild(novoCard);
                }
            }
        });
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

        // Filtrar por data
        if (this.filtros.date && this.filtros.date !== 'todos') {
            // Usar formato de string YYYY-MM-DD para evitar problemas de timezone
            const hoje = new Date();
            const hojeStr = hoje.toISOString().split('T')[0]; // YYYY-MM-DD

            const amanha = new Date(hoje);
            amanha.setDate(amanha.getDate() + 1);
            const amanhaStr = amanha.toISOString().split('T')[0];

            const fimSemana = new Date(hoje);
            fimSemana.setDate(fimSemana.getDate() + 7);
            const fimSemanaStr = fimSemana.toISOString().split('T')[0];

            filtered = filtered.filter(p => {
                // p.dia_entrega já vem no formato YYYY-MM-DD
                const dataEntregaStr = p.dia_entrega;

                if (this.filtros.date === 'hoje') {
                    return dataEntregaStr === hojeStr;
                } else if (this.filtros.date === 'amanha') {
                    return dataEntregaStr === amanhaStr;
                } else if (this.filtros.date === 'semana') {
                    return dataEntregaStr >= hojeStr && dataEntregaStr <= fimSemanaStr;
                }
                return true;
            });
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

        // Renderizar filtrados usando atualização inteligente
        const container = document.getElementById('pedidos-container');
        if (container) {
            // Se já tem cards, fazer update inteligente
            if (container.children.length > 0) {
                // Temporariamente atualizar lista de pedidos para exibir apenas os filtrados
                const pedidosOriginais = [...this.pedidos];
                this.pedidos = filtered;
                this.updatePedidosInteligente();
                this.pedidos = pedidosOriginais; // Restaurar lista completa
            } else {
                // Primeira renderização - criar todos os cards
                container.innerHTML = '';

                if (filtered.length === 0) {
                    container.innerHTML = this.getEmptyState();
                } else {
                    filtered.forEach(pedido => {
                        const card = PedidoCard.create(pedido, this.modoSelecao, this.pedidosSelecionados.has(pedido.id));
                        // Aplicar animação apenas se for pedido novo
                        if (!pedido.novo) {
                            card.classList.add('no-animation');
                        }
                        container.appendChild(card);
                    });
                }
            }
        }

        // Garantir que os botões de filtro permaneçam com estilo correto
        this.updateFilterButtons();
    },

    /**
     * Atualiza estilo visual dos botões de filtro
     */
    updateFilterButtons() {
        // Atualizar botões de data
        document.querySelectorAll('[data-filter-date]').forEach(btn => {
            const filterValue = btn.getAttribute('data-filter-date');
            // Limpar todas as classes de estado
            btn.classList.remove('active', 'bg-primary', 'text-white', 'bg-gray-200', 'text-gray-700', 'hover:bg-gray-300');

            if (filterValue === this.filtros.date) {
                // Botão ativo
                btn.classList.add('active', 'bg-primary', 'text-white');
            } else {
                // Botão inativo
                btn.classList.add('bg-gray-200', 'text-gray-700', 'hover:bg-gray-300');
            }
        });

        // Atualizar botões de status
        document.querySelectorAll('[data-filter-status]').forEach(btn => {
            const filterValue = btn.getAttribute('data-filter-status');
            const statusAtivo = this.filtros.status || 'todos';

            // Limpar todas as classes de estado
            btn.classList.remove('active', 'bg-primary', 'text-white', 'bg-gray-200', 'text-gray-700', 'hover:bg-gray-300');

            if (filterValue === statusAtivo) {
                // Botão ativo
                btn.classList.add('active', 'bg-primary', 'text-white');
            } else {
                // Botão inativo
                btn.classList.add('bg-gray-200', 'text-gray-700', 'hover:bg-gray-300');
            }
        });
    },

    /**
     * Define filtro de data
     */
    setDateFilter(date) {
        this.filtros.date = date;

        // Atualizar botões ativos
        this.updateFilterButtons();

        // Aplicar filtro
        this.filterPedidos();
    },

    /**
     * Define filtro de status
     */
    setStatusFilter(status) {
        this.filtros.status = status === 'todos' ? '' : status;

        // Atualizar botões ativos
        this.updateFilterButtons();

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
     * Ativa/desativa modo de seleção de pedidos
     */
    toggleModoSelecao() {
        this.modoSelecao = !this.modoSelecao;
        this.pedidosSelecionados.clear();

        const btnRota = document.getElementById('btn-rota-otimizada');

        if (this.modoSelecao) {
            // Modo seleção ativado
            if (btnRota) {
                btnRota.innerHTML = '<i class="fas fa-check-circle"></i> <span class="hidden sm:inline">Confirmar Seleção</span>';
                btnRota.classList.remove('bg-green-100', 'text-green-700');
                btnRota.classList.add('bg-primary', 'text-white');
            }
            Notification.info('Modo de seleção ativado. Selecione os pedidos para calcular a rota.');
        } else {
            // Modo seleção desativado
            if (btnRota) {
                btnRota.innerHTML = '<i class="fas fa-map-marked-alt"></i> <span class="hidden sm:inline">Rota Otimizada</span>';
                btnRota.classList.remove('bg-primary', 'text-white');
                btnRota.classList.add('bg-green-100', 'text-green-700');
            }
        }

        // Re-renderizar pedidos para mostrar/ocultar checkboxes
        // Forçar animação/re-render completo para garantir que os checkboxes apareçam
        this.renderPedidos(true);
    },

    /**
     * Toggle seleção de um pedido
     */
    toggleSelecaoPedido(pedidoId) {
        if (this.pedidosSelecionados.has(pedidoId)) {
            this.pedidosSelecionados.delete(pedidoId);
        } else {
            this.pedidosSelecionados.add(pedidoId);
        }

        // Atualizar visual do card
        const card = document.querySelector(`.pedido-card[data-id="${pedidoId}"]`);
        if (card) {
            const checkbox = card.querySelector('input[type="checkbox"]');
            if (checkbox) {
                checkbox.checked = this.pedidosSelecionados.has(pedidoId);
            }
            card.classList.toggle('selected', this.pedidosSelecionados.has(pedidoId));
        }

        // Atualizar contador no botão
        this.atualizarContadorSelecao();
    },

    /**
     * Atualiza contador de pedidos selecionados no botão
     */
    atualizarContadorSelecao() {
        const btnRota = document.getElementById('btn-rota-otimizada');
        const count = this.pedidosSelecionados.size;

        if (btnRota && this.modoSelecao) {
            if (count > 0) {
                btnRota.innerHTML = `<i class="fas fa-check-circle"></i> <span class="hidden sm:inline">Calcular Rota (${count})</span>`;
            } else {
                btnRota.innerHTML = '<i class="fas fa-check-circle"></i> <span class="hidden sm:inline">Confirmar Seleção</span>';
            }
        }
    },

    /**
     * Calcula rota otimizada para os pedidos selecionados
     */
    async calcularRotaOtimizada() {
        const btnRota = document.getElementById('btn-rota-otimizada');

        // Se estiver em modo seleção, calcular rota com pedidos selecionados
        if (this.modoSelecao) {
            const pedidosSelecionados = Array.from(this.pedidosSelecionados);

            if (pedidosSelecionados.length < 2) {
                Notification.warning('Selecione pelo menos 2 pedidos para calcular a rota otimizada.');
                return;
            }

            // Verificar se os pedidos selecionados têm distância calculada
            const pedidosComDistancia = this.pedidos.filter(p =>
                pedidosSelecionados.includes(p.id) &&
                p.distancia_km !== null &&
                p.distancia_km !== undefined &&
                p.tipo_pedido === 'Entrega'
            );

            if (pedidosComDistancia.length < 2) {
                Notification.warning('É necessário que pelo menos 2 pedidos selecionados tenham distância calculada e sejam do tipo Entrega.');
                return;
            }

            // Desativar modo seleção
            this.modoSelecao = false;
            this.renderPedidos();

            // Calcular rota
            await this.executarCalculoRota(pedidosComDistancia.map(p => p.id));
            return;
        }

        // Se não estiver em modo seleção, ativar modo seleção
        this.toggleModoSelecao();
    },

    /**
     * Executa o cálculo da rota otimizada
     */
    async executarCalculoRota(pedidoIds) {
        const btnRota = document.getElementById('btn-rota-otimizada');

        try {
            // Atualizar botão para mostrar loading
            if (btnRota) {
                btnRota.innerHTML = '<i class="fas fa-spinner fa-spin"></i> <span class="hidden sm:inline">Calculando...</span>';
                btnRota.disabled = true;
            }

            Notification.info('Calculando rota otimizada... Isso pode levar alguns segundos.');

            // Chamar API para calcular rota otimizada
            const timeoutPromise = new Promise((_, reject) =>
                setTimeout(() => reject(new Error('Timeout - tente novamente')), 120000)
            );

            const apiPromise = API.calcularRotaOtimizada(pedidoIds);
            const result = await Promise.race([apiPromise, timeoutPromise]);

            if (result && result.success) {
                const rota = result.data;

                Notification.success(`Rota otimizada calculada! ${rota.distancia_total_km} km, ${rota.duracao_total_min} min`);

                // Limpar seleção
                this.pedidosSelecionados.clear();

                // Redirecionar para página de visualização da rota
                window.location.href = `/pages/rota-entrega.html?id=${rota.rota_id}`;
            } else {
                throw new Error(result?.error || 'Erro ao calcular rota otimizada');
            }

        } catch (error) {
            console.error('Erro ao calcular rota otimizada:', error);
            Notification.error(`Erro: ${error.message || 'Falha ao calcular rota otimizada'}`);
        } finally {
            // Restaurar botão
            if (btnRota) {
                btnRota.innerHTML = '<i class="fas fa-map-marked-alt"></i> <span class="hidden sm:inline">Rota Otimizada</span>';
                btnRota.classList.remove('bg-primary', 'text-white');
                btnRota.classList.add('bg-green-100', 'text-green-700');
                btnRota.disabled = false;
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

            // Usar refreshPedidos que mantém filtros e detecta novos pedidos
            this.refreshPedidos(false);
            this.loadStats();
        }, this.autoRefreshTime);
    },

    /**
     * Para auto-refresh
     */
    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
        }
    },

    /**
     * Limpa recursos ao sair do painel
     */
    cleanup() {
        this.stopAutoRefresh();
    }
};

// Expor PainelManager globalmente para acesso via onclick
window.PainelManager = PainelManager;

// Parar auto-refresh ao navegar para outra página
window.addEventListener('beforeunload', () => {
    if (typeof PainelManager !== 'undefined') {
        PainelManager.cleanup();
    }
});

