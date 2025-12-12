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
            const response = await fetch(url, config);
            
            // Tentar parsear JSON, mas pode não ser JSON em caso de erro
            let data;
            try {
                data = await response.json();
            } catch (e) {
                data = { error: `Erro ${response.status}` };
            }

            if (!response.ok) {
                // Se for erro 401 e requer autenticação, tentar novamente após login
                if (response.status === 401 && needsAuth && typeof Auth !== 'undefined') {
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
                
                throw new Error(data.error || data.message || `Erro ${response.status}`);
            }

            return { success: true, data, status: response.status };
        } catch (error) {
            console.error('API Error:', error);
            
            // Se está offline, tentar usar cache do IndexedDB
            if (!Utils.isOnline()) {
                return { success: false, offline: true, error: error.message };
            }
            
            return { success: false, error: error.message };
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
    }
};

// Interceptor global de erros
window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
    
    if (!Utils.isOnline()) {
        Notification.show('Sem conexão com a internet', 'warning');
    }
});

