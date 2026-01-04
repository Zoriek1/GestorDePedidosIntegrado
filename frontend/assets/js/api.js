/**
 * Plante Uma Flor - PWA v3.0
 * API Client - Wrapper para chamadas ao backend
 */

const API = {
    baseURL: window.location.origin,

    /**
     * Parseia resposta HTTP de forma robusta
     * @param {Response} response - Objeto Response do fetch
     * @returns {Promise<{data: any, isJson: boolean, parseError: Error|null}>}
     */
    async parseResponse(response) {
        // 204 No Content - não tem body
        if (response.status === 204) {
            return { data: null, isJson: false, parseError: null };
        }

        // Verificar Content-Type se disponível
        const contentType = response.headers.get('content-type');
        const isLikelyJson = contentType && contentType.includes('application/json');

        try {
            const text = await response.text();
            
            // Se não há texto, retornar null
            if (!text || text.trim() === '') {
                return { data: null, isJson: false, parseError: null };
            }

            // Tentar parsear como JSON se parece ser JSON
            if (isLikelyJson || text.trim().startsWith('{') || text.trim().startsWith('[')) {
                try {
                    const parsed = JSON.parse(text);
                    return { data: parsed, isJson: true, parseError: null };
                } catch (e) {
                    // Se falhou parsear como JSON mas tinha indicação de JSON, retornar erro
                    if (isLikelyJson) {
                        return { data: null, isJson: false, parseError: e };
                    }
                    // Caso contrário, retornar como texto
                    return { data: text, isJson: false, parseError: null };
                }
            }

            // Retornar como texto
            return { data: text, isJson: false, parseError: null };
        } catch (e) {
            return { data: null, isJson: false, parseError: e };
        }
    },

    /**
     * Verifica se uma rota requer autenticação
     * @param {string} endpoint - Endpoint da API
     * @param {string} method - Método HTTP
     * @returns {boolean} True se requer autenticação
     */
    requiresAuth(endpoint, method) {
        // Remover query string do endpoint para verificação
        const pathname = endpoint.split('?')[0];
        
        // Apenas rotas críticas requerem autenticação
        const criticalRoutes = [
            { path: '/api/pedidos', method: 'POST' },  // Criar pedido
            { path: '/api/exportar-planilha', method: 'POST' },  // Exportar planilha
        ];
        
        // DELETE /api/pedidos/<id> - verificar por padrão (aceita UUIDs e IDs não-numéricos)
        if (method === 'DELETE' && pathname.match(/^\/api\/pedidos\/[^\/]+$/)) {
            return true;
        }
        
        // Verificar outras rotas críticas usando startsWith para prefixos
        return criticalRoutes.some(route => 
            pathname.startsWith(route.path) && method === route.method
        );
    },
    
    /**
     * Gera ID único para requisição (Phase 0)
     */
    generateRequestId() {
        return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    },

    /**
     * Faz requisição HTTP
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const method = options.method || 'GET';
        
        // Gerar requestId para rastreamento (Phase 0)
        const requestId = this.generateRequestId();
        const startTime = Date.now();
        
        // Log request (Phase 0)
        if (typeof Telemetry !== 'undefined') {
            Telemetry.logInfo('api', 'request', `API request: ${method} ${endpoint}`, {
                method,
                url: endpoint,
                requestId
            }, requestId);
        }
        
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
        
        // Headers condicionais: só Content-Type quando há body JSON
        const headers = {
            'Accept': 'application/json',
            ...options.headers
        };
        
        // Só adicionar Content-Type se for POST/PUT e houver body
        if ((method === 'POST' || method === 'PUT') && options.body) {
            headers['Content-Type'] = 'application/json';
        }
        
        // Adicionar header de autenticação se necessário
        if (needsAuth && typeof Auth !== 'undefined') {
            const authHeader = Auth.getAuthHeader();
            Object.assign(headers, authHeader);
        }
        
        // Timeout com AbortController (ajustar para 15s se não especificado - Phase 0)
        const timeoutMs = options.timeoutMs ?? 15000;
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
        
        const config = {
            method,
            headers,
            ...options,
            signal: controller.signal
        };

        try {
            const response = await fetch(url, config);
            clearTimeout(timeoutId);
            
            const durationMs = Date.now() - startTime;
            
            // Log response (Phase 0)
            if (typeof Telemetry !== 'undefined') {
                Telemetry.logInfo('api', 'response', `API response: ${method} ${endpoint}`, {
                    requestId,
                    status: response.status,
                    durationMs
                }, requestId);
            }
            
            // Usar parseResponse() unificada
            const parseResult = await this.parseResponse(response);
            
            // Se houve erro de parse, tratar adequadamente
            if (parseResult.parseError) {
                console.warn(`[API] Erro ao parsear resposta:`, parseResult.parseError);
                // Se response.ok, ainda pode ser sucesso (resposta não-JSON válida)
                if (response.ok) {
                    return { 
                        success: true, 
                        data: parseResult.data || null, 
                        status: response.status 
                    };
                }
                // Se não ok, tratar como erro
                throw new Error(`Erro ${response.status} - Resposta não é JSON válido`);
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
                        // Criar novo AbortController para retry
                        const retryController = new AbortController();
                        const retryTimeoutId = setTimeout(() => retryController.abort(), timeoutMs);
                        
                        try {
                            // Tentar novamente com novas credenciais
                            const authHeader = Auth.getAuthHeader();
                            const retryConfig = {
                                ...config,
                                signal: retryController.signal,
                                headers: {
                                    ...config.headers,
                                    ...authHeader
                                }
                            };
                            
                            const retryResponse = await fetch(url, retryConfig);
                            clearTimeout(retryTimeoutId);
                            
                            // Usar parseResponse() no retry também
                            const retryParseResult = await this.parseResponse(retryResponse);
                            
                            if (retryParseResult.parseError) {
                                console.warn(`[API] Erro ao parsear resposta do retry:`, retryParseResult.parseError);
                                if (retryResponse.ok) {
                                    return { 
                                        success: true, 
                                        data: retryParseResult.data || null, 
                                        status: retryResponse.status 
                                    };
                                }
                                throw new Error(`Erro ${retryResponse.status} - Resposta não é JSON válido`);
                            }
                            
                            if (!retryResponse.ok) {
                                // Preservar erro do backend se for JSON
                                const errorMsg = retryParseResult.isJson && retryParseResult.data 
                                    ? (retryParseResult.data.error || retryParseResult.data.message || `Erro ${retryResponse.status}`)
                                    : `Erro ${retryResponse.status}`;
                                throw new Error(errorMsg);
                            }
                            
                            // Sucesso no retry
                            return { 
                                success: true, 
                                data: retryParseResult.data, 
                                status: retryResponse.status 
                            };
                        } catch (retryError) {
                            clearTimeout(retryTimeoutId);
                            throw retryError;
                        }
                    }
                }
                
                // Preservar erro do backend se for JSON
                const errorMsg = parseResult.isJson && parseResult.data
                    ? (parseResult.data.error || parseResult.data.message || `Erro ${response.status}`)
                    : `Erro ${response.status}`;
                
                console.error(`[API] Erro na resposta:`, { 
                    status: response.status, 
                    error: errorMsg, 
                    data: parseResult.data 
                });
                
                // Log error (Phase 0)
                if (typeof Telemetry !== 'undefined') {
                    Telemetry.logError('api', 'error', new Error(errorMsg), {
                        requestId,
                        url: endpoint,
                        status: response.status,
                        errorType: 'http_error'
                    }, requestId);
                }
                
                // Normalize error response (Phase 0)
                return {
                    ok: false,
                    success: false,
                    status: response.status,
                    code: `HTTP_${response.status}`,
                    message: errorMsg,
                    details: parseResult.isJson ? parseResult.data : null,
                    requestId
                };
            }

            // Sucesso: response.ok e sem erro de parse
            return { 
                ok: true,
                success: true, 
                data: parseResult.data, 
                status: response.status,
                requestId
            };
        } catch (error) {
            clearTimeout(timeoutId);
            
            const durationMs = Date.now() - startTime;
            
            console.error('[API] Erro na requisição:', { 
                endpoint, 
                method, 
                error: error.message, 
                name: error.name,
                stack: error.stack 
            });
            
            // Log error (Phase 0)
            if (typeof Telemetry !== 'undefined') {
                Telemetry.logError('api', 'error', error, {
                    requestId,
                    url: endpoint,
                    method,
                    durationMs,
                    errorType: error.name || 'unknown'
                }, requestId);
            }
            
            // Normalize error responses (Phase 0)
            // Tratar AbortError (timeout)
            if (error.name === 'AbortError') {
                return { 
                    ok: false,
                    success: false, 
                    error: 'Timeout na requisição',
                    code: 'TIMEOUT',
                    message: 'Timeout na requisição',
                    timeout: true,
                    requestId
                };
            }
            
            // Se está offline, tentar usar cache do IndexedDB
            if (typeof Utils !== 'undefined' && !Utils.isOnline()) {
                return { 
                    ok: false,
                    success: false, 
                    offline: true, 
                    error: error.message,
                    code: 'OFFLINE',
                    message: error.message,
                    requestId
                };
            }
            
            // NetworkError específico
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                return { 
                    ok: false,
                    success: false, 
                    error: 'Erro de conexão. Verifique sua internet e se o servidor está rodando.',
                    code: 'NETWORK_ERROR',
                    message: 'Erro de conexão. Verifique sua internet e se o servidor está rodando.',
                    networkError: true,
                    requestId
                };
            }
            
            return { 
                ok: false,
                success: false, 
                error: error.message || 'Erro desconhecido na requisição',
                code: 'UNKNOWN_ERROR',
                message: error.message || 'Erro desconhecido na requisição',
                requestId
            };
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
     * Obter pedidos por data (retorna contagem por horário)
     * @param {string} data - Data no formato YYYY-MM-DD ou DD/MM/YYYY
     */
    async getPedidosPorData(data) {
        return this.get(`/api/pedidos/por-data?data=${encodeURIComponent(data)}`);
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
        
        try {
            const result = await this.post(url);
            
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

// Interceptor global de erros (Phase 0: também logar em telemetry)
window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
    
    // Log to telemetry (Phase 0)
    if (typeof Telemetry !== 'undefined') {
        const reason = event.reason;
        Telemetry.logError('api', 'unhandledRejection', reason instanceof Error ? reason : new Error(String(reason)), {
            reason: String(reason).substring(0, 200)
        });
    }
    
    if (typeof Utils !== 'undefined' && !Utils.isOnline()) {
        if (typeof Notification !== 'undefined') {
            Notification.show('Sem conexão com a internet', 'warning');
        }
    }
});

