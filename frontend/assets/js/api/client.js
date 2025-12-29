/**
 * API Client - Cliente único centralizado para chamadas ao backend
 * Versão refatorada e organizada do api.js
 */

class APIClient {
    constructor(baseURL = window.location.origin) {
        this.baseURL = baseURL;
        this.timeout = 10000;
    }

    /**
     * Faz requisição HTTP
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const method = options.method || 'GET';
        
        // Headers
        const headers = {
            'Accept': 'application/json',
            ...options.headers
        };
        
        if ((method === 'POST' || method === 'PUT') && options.body) {
            headers['Content-Type'] = 'application/json';
        }
        
        // Verificar autenticação se necessário
        if (typeof Auth !== 'undefined' && this.requiresAuth(endpoint, method)) {
            if (!Auth.isAuthenticated()) {
                const creds = await Auth.promptPassword(
                    'Esta ação requer autenticação. Por favor, faça login para continuar.'
                );
                if (!creds) {
                    return { success: false, error: 'Autenticação cancelada', cancelled: true };
                }
            }
            const authHeader = Auth.getAuthHeader();
            Object.assign(headers, authHeader);
        }
        
        // Timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);
        
        try {
            const response = await fetch(url, {
                method,
                headers,
                body: options.body ? (typeof options.body === 'string' ? options.body : JSON.stringify(options.body)) : undefined,
                signal: controller.signal,
                ...options
            });
            
            clearTimeout(timeoutId);
            
            // Parse response
            const data = await this.parseResponse(response);
            
            return {
                success: response.ok,
                data: data,
                status: response.status,
                response: response
            };
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                return { success: false, error: 'Timeout na requisição', timeout: true };
            }
            if (typeof Utils !== 'undefined' && !Utils.isOnline()) {
                return { success: false, offline: true, error: error.message };
            }
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                return { 
                    success: false, 
                    error: 'Erro de conexão. Verifique sua internet e se o servidor está rodando.',
                    networkError: true
                };
            }
            return { success: false, error: error.message || 'Erro desconhecido na requisição' };
        }
    }

    async parseResponse(response) {
        if (response.status === 204) return null;
        
        const contentType = response.headers.get('content-type');
        const text = await response.text();
        
        if (contentType && contentType.includes('application/json')) {
            return text ? JSON.parse(text) : null;
        }
        
        return text || null;
    }

    requiresAuth(endpoint, method) {
        const pathname = endpoint.split('?')[0];
        const criticalRoutes = [
            { path: '/api/pedidos', method: 'POST' },
            { path: '/api/exportar-planilha', method: 'POST' },
        ];
        
        if (method === 'DELETE' && pathname.match(/^\/api\/pedidos\/[^\/]+$/)) {
            return true;
        }
        
        return criticalRoutes.some(route => 
            pathname.startsWith(route.path) && method === route.method
        );
    }

    // Métodos HTTP
    async get(endpoint, options = {}) {
        return this.request(endpoint, { ...options, method: 'GET' });
    }

    async post(endpoint, data, options = {}) {
        return this.request(endpoint, { ...options, method: 'POST', body: data });
    }

    async put(endpoint, data, options = {}) {
        return this.request(endpoint, { ...options, method: 'PUT', body: data });
    }

    async delete(endpoint, options = {}) {
        return this.request(endpoint, { ...options, method: 'DELETE' });
    }

    // Métodos específicos da API - Pedidos
    async getPedidos(filters = {}) {
        const params = new URLSearchParams();
        if (filters.status) params.append('status', filters.status);
        if (filters.limit) params.append('limit', filters.limit);
        if (filters.search) params.append('search', filters.search);
        if (filters.data_inicio) params.append('data_inicio', filters.data_inicio);
        if (filters.data_fim) params.append('data_fim', filters.data_fim);
        
        const queryString = params.toString();
        const endpoint = `/api/pedidos${queryString ? `?${queryString}` : ''}`;
        return this.get(endpoint);
    }

    async getPedido(pedidoId) {
        return this.get(`/api/pedidos/${pedidoId}`);
    }

    async createPedido(pedidoData) {
        return this.post('/api/pedidos', pedidoData);
    }

    async updatePedido(pedidoId, pedidoData) {
        return this.put(`/api/pedidos/${pedidoId}`, pedidoData);
    }

    async deletePedido(pedidoId) {
        return this.delete(`/api/pedidos/${pedidoId}`);
    }

    async updatePedidoStatus(pedidoId, novoStatus) {
        return this.put(`/api/pedidos/${pedidoId}/status`, { status: novoStatus });
    }

    async getPedidosPorData(data) {
        return this.get(`/api/pedidos/por-data?data=${encodeURIComponent(data)}`);
    }

    async calcularDistanciaPedido(pedidoId) {
        return this.get(`/api/pedidos/${pedidoId}/distancia`);
    }

    async calcularTaxaEntrega(pedidoId) {
        return this.post(`/api/pedidos/${pedidoId}/calcular-taxa`);
    }

    // Métodos específicos - Estatísticas
    async getStats() {
        return this.get('/api/stats');
    }

    async getOverduePedidos() {
        return this.get('/api/pedidos/overdue');
    }

    async healthCheck() {
        return this.get('/api/health');
    }

    // Métodos específicos - Export
    async exportarPlanilha() {
        return this.post('/api/exportar-planilha', {});
    }

    // Métodos específicos - Fontes
    async getFontesPedido() {
        return this.get('/api/fontes-pedido');
    }
}

// Exportar instância global
const apiClient = new APIClient();

