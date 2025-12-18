/**
 * Plante Uma Flor - PWA v3.0
 * API Client - Wrapper para chamadas ao backend
 */

const API = {
    baseURL: window.location.origin,

    /**
     * Verifica se uma rota requer autenticação
     * @param {string} endpoint - Endpoint da API
     * @param {string} method - Método HTTP
     * @returns {boolean} True se requer autenticação
     */
    requiresAuth(endpoint, method) {
        // Apenas rotas críticas requerem autenticação
        const criticalRoutes = [
            { path: '/api/pedidos', method: 'POST' },  // Criar pedido
            { path: '/api/exportar-planilha', method: 'POST' },  // Exportar planilha
        ];
        
        // DELETE /api/pedidos/<id> - verificar por padrão
        if (method === 'DELETE' && endpoint.startsWith('/api/pedidos/') && 
            endpoint.match(/^\/api\/pedidos\/\d+$/)) {
            return true;
        }
        
        // Verificar outras rotas críticas
        return criticalRoutes.some(route => 
            endpoint === route.path && method === route.method
        );
    },
    
    /**
     * Faz requisição HTTP
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const method = options.method || 'GET';
        
        // Verificar se esta rota requer autenticação
        const needsAuth = this.requiresAuth(endpoint, method);
        
        // Se requer autenticação e não está autenticado, pedir senha
        if (needsAuth && typeof Auth !== 'undefined' && !Auth.isAuthenticated()) {
            const creds = await Auth.promptPassword(
                'Esta ação requer autenticação. Por favor, faça login para continuar.'
            );
            
            if (!creds) {
                return { 
                    success: false, 
                    error: 'Autenticação cancelada',
                    cancelled: true 
                };
            }
        }
        
        // Adicionar header de autenticação se necessário
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };
        
        if (needsAuth && typeof Auth !== 'undefined') {
            const authHeader = Auth.getAuthHeader();
            Object.assign(headers, authHeader);
        }
        
        const config = {
            headers,
            ...options
        };

        try {
            console.log(`[API] ${method} ${endpoint}`, { needsAuth, hasBody: !!options.body });
            const response = await fetch(url, config);
            
            console.log(`[API] Resposta recebida:`, { status: response.status, ok: response.ok, url });
            
            // Tentar parsear JSON, mas pode não ser JSON em caso de erro
            let data;
            try {
                const text = await response.text();
                console.log(`[API] Resposta texto:`, text.substring(0, 200));
                data = text ? JSON.parse(text) : {};
            } catch (e) {
                console.warn(`[API] Erro ao parsear JSON:`, e);
                data = { error: `Erro ${response.status} - Resposta não é JSON válido` };
            }

            if (!response.ok) {
                // Se for erro 401 e requer autenticação, tentar novamente após login
                if (response.status === 401 && needsAuth && typeof Auth !== 'undefined') {
                    console.log('[API] Erro 401 - Tentando reautenticar...');
                    // Limpar credenciais inválidas
                    Auth.logout();
                    
                    // Pedir senha novamente
                    const creds = await Auth.promptPassword(
                        'Credenciais inválidas ou expiradas. Por favor, faça login novamente.'
                    );
                    
                    if (creds) {
                        // Tentar novamente com novas credenciais
                        const authHeader = Auth.getAuthHeader();
                        const retryConfig = {
                            ...config,
                            headers: {
                                ...config.headers,
                                ...authHeader
                            }
                        };
                        
                        const retryResponse = await fetch(url, retryConfig);
                        const retryData = await retryResponse.json();
                        
                        if (!retryResponse.ok) {
                            throw new Error(retryData.error || `Erro ${retryResponse.status}`);
                        }
                        
                        return { success: true, data: retryData, status: retryResponse.status };
                    }
                }
                
                const errorMsg = data.error || data.message || `Erro ${response.status}`;
                console.error(`[API] Erro na resposta:`, { status: response.status, error: errorMsg, data });
                throw new Error(errorMsg);
            }

            return { success: true, data, status: response.status };
        } catch (error) {
            console.error('[API] Erro na requisição:', { 
                endpoint, 
                method, 
                error: error.message, 
                name: error.name,
                stack: error.stack 
            });
            
            // Se está offline, tentar usar cache do IndexedDB
            if (!Utils.isOnline()) {
                return { success: false, offline: true, error: error.message };
            }
            
            // NetworkError específico
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                return { 
                    success: false, 
                    error: 'Erro de conexão. Verifique sua internet e se o servidor está rodando.',
                    networkError: true
                };
            }
            
            return { success: false, error: error.message || 'Erro desconhecido na requisição' };
        }
    },

    /**
     * GET - Obter recurso
     */
    async get(endpoint) {
        return this.request(endpoint, {
            method: 'GET'
        });
    },

    /**
     * POST - Criar recurso
     */
    async post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    /**
     * PUT - Atualizar recurso
     */
    async put(endpoint, data) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    /**
     * DELETE - Deletar recurso
     */
    async delete(endpoint) {
        return this.request(endpoint, {
            method: 'DELETE'
        });
    },

    // ==================== ENDPOINTS DE PEDIDOS ====================

    /**
     * Criar novo pedido
     */
    async createPedido(pedidoData) {
        return this.post('/api/pedidos', pedidoData);
    },

    /**
     * Listar todos os pedidos
     */
    async getPedidos(filters = {}) {
        let endpoint = '/api/pedidos';
        const params = new URLSearchParams();

        if (filters.status) {
            params.append('status', filters.status);
        }

        if (filters.limit) {
            params.append('limit', filters.limit);
        }

        if (filters.search) {
            params.append('search', filters.search);
        }

        const queryString = params.toString();
        if (queryString) {
            endpoint += `?${queryString}`;
        }

        return this.get(endpoint);
    },

    /**
     * Obter pedido específico
     */
    async getPedido(pedidoId) {
        return this.get(`/api/pedidos/${pedidoId}`);
    },

    /**
     * Atualizar status do pedido
     */
    async updatePedidoStatus(pedidoId, novoStatus) {
        return this.put(`/api/pedidos/${pedidoId}/status`, {
            status: novoStatus
        });
    },

    /**
     * Marcar pedido como impresso
     */
    async marcarImpresso(pedidoId) {
        const url = `/api/pedidos/${pedidoId}/marcar-impresso`;
        console.log(`[API] marcarImpresso(${pedidoId}) - URL: ${url}`);
        
        try {
            console.log(`[API] Enviando requisição POST para ${url}`);
            const result = await this.post(url);
            console.log(`[API] Resposta recebida:`, { 
                success: result.success, 
                status: result.status,
                data: result.data 
            });
            
            if (!result.success) {
                console.error(`[API] Erro na resposta:`, result.error);
            }
            
            return result;
        } catch (error) {
            console.error(`[API] Erro na requisição marcarImpresso:`, error);
            throw error;
        }
    },

    /**
     * Atualizar pedido completo
     */
    async updatePedido(pedidoId, pedidoData) {
        return this.put(`/api/pedidos/${pedidoId}`, pedidoData);
    },

    /**
     * Deletar pedido
     */
    async deletePedido(pedidoId) {
        return this.delete(`/api/pedidos/${pedidoId}`);
    },

    /**
     * Obter estatísticas
     */
    async getStats() {
        return this.get('/api/stats');
    },

    /**
     * Obter pedidos atrasados
     */
    async getOverduePedidos() {
        return this.get('/api/pedidos/overdue');
    },

    /**
     * Limpar pedidos antigos
     */
    async cleanupOldPedidos(days = 1) {
        return this.post('/api/cleanup', { days });
    },

    /**
     * Health check
     */
    async healthCheck() {
        return this.get('/api/health');
    },

    // ==================== ENDPOINTS DE DISTÂNCIA ====================

    /**
     * Calcular distância de um pedido específico
     */
    async calcularDistanciaPedido(pedidoId) {
        return this.get(`/api/pedidos/${pedidoId}/distancia`);
    },

    /**
     * Calcular distâncias em lote
     * @param {Array} pedidoIds - Array de IDs dos pedidos (opcional, se vazio calcula todos)
     * @param {Boolean} forceRecalc - Forçar recálculo mesmo se já tiver cache
     */
    async calcularDistanciasLote(pedidoIds = [], forceRecalc = false) {
        return this.post('/api/pedidos/calcular-distancias', {
            pedido_ids: pedidoIds,
            force_recalc: forceRecalc
        });
    },

    /**
     * Calcular taxa de entrega para um pedido
     * @param {Number} pedidoId - ID do pedido
     */
    async calcularTaxaEntrega(pedidoId) {
        return this.post(`/api/pedidos/${pedidoId}/calcular-taxa`);
    },

    /**
     * Calcular rota otimizada para múltiplos pedidos
     * @param {Array} pedidoIds - Array de IDs dos pedidos (opcional, se vazio calcula todos elegíveis)
     * @param {String} nome - Nome da rota (opcional)
     */
    async calcularRotaOtimizada(pedidoIds = [], nome = 'Rota Otimizada') {
        return this.post('/api/pedidos/rota-otimizada', {
            pedido_ids: pedidoIds,
            nome: nome
        });
    },

    /**
     * Obter detalhes de uma rota otimizada
     * @param {Number} rotaId - ID da rota
     */
    async obterRotaOtimizada(rotaId) {
        return this.get(`/api/pedidos/rota-otimizada/${rotaId}`);
    },

    // ==================== ENDPOINTS DE FONTES DE PEDIDO ====================

    /**
     * Listar fontes de pedido (apenas ativas)
     */
    async getFontesPedido() {
        return this.get('/api/fontes-pedido');
    },

    /**
     * Listar todas as fontes (ativas e inativas)
     */
    async getAllFontesPedido() {
        return this.get('/api/fontes-pedido/all');
    },

    /**
     * Criar nova fonte de pedido
     * @param {Object} data - { nome, ativo }
     */
    async createFontePedido(data) {
        return this.post('/api/fontes-pedido', data);
    },

    /**
     * Atualizar fonte de pedido
     * @param {Number} id - ID da fonte
     * @param {Object} data - { nome, ativo }
     */
    async updateFontePedido(id, data) {
        return this.put(`/api/fontes-pedido/${id}`, data);
    },

    /**
     * Desativar fonte de pedido (soft delete)
     * @param {Number} id - ID da fonte
     */
    async deleteFontePedido(id) {
        return this.delete(`/api/fontes-pedido/${id}`);
    }
};

// Interceptor global de erros
window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
    
    if (!Utils.isOnline()) {
        Notification.show('Sem conexão com a internet', 'warning');
    }
});

