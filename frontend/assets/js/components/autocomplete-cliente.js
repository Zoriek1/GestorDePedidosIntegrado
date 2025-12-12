/**
 * Componente Autocomplete de Clientes
 * Busca clientes em tempo real e permite seleção para preenchimento automático
 */

class AutocompleteCliente {
    constructor(options = {}) {
        this.inputElement = options.inputElement;
        this.resultsElement = options.resultsElement;
        this.onSelect = options.onSelect || (() => {});
        this.debounceTimeout = null;
        this.selectedIndex = -1;
        this.results = [];
        
        this.init();
    }
    
    init() {
        if (!this.inputElement || !this.resultsElement) {
            console.error('AutocompleteCliente: elementos obrigatórios não fornecidos');
            return;
        }
        
        // Event listeners
        this.inputElement.addEventListener('input', (e) => this.handleInput(e));
        this.inputElement.addEventListener('keydown', (e) => this.handleKeydown(e));
        this.inputElement.addEventListener('focus', () => {
            if (this.inputElement.value.length >= 2) {
                this.search(this.inputElement.value);
            }
        });
        
        // Fechar ao clicar fora
        document.addEventListener('click', (e) => {
            if (!this.inputElement.contains(e.target) && !this.resultsElement.contains(e.target)) {
                this.hideResults();
            }
        });
    }
    
    handleInput(e) {
        const query = e.target.value.trim();
        
        // Limpar timeout anterior
        if (this.debounceTimeout) {
            clearTimeout(this.debounceTimeout);
        }
        
        // Buscar após 300ms sem digitação
        if (query.length >= 2) {
            this.debounceTimeout = setTimeout(() => {
                this.search(query);
            }, 300);
        } else {
            this.hideResults();
        }
    }
    
    handleKeydown(e) {
        if (!this.resultsElement.classList.contains('active')) return;
        
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.selectedIndex = Math.min(this.selectedIndex + 1, this.results.length - 1);
                this.highlightResult();
                break;
            
            case 'ArrowUp':
                e.preventDefault();
                this.selectedIndex = Math.max(this.selectedIndex - 1, -1);
                this.highlightResult();
                break;
            
            case 'Enter':
                e.preventDefault();
                if (this.selectedIndex >= 0 && this.results[this.selectedIndex]) {
                    this.selectCliente(this.results[this.selectedIndex]);
                }
                break;
            
            case 'Escape':
                this.hideResults();
                break;
        }
    }
    
    async search(query) {
        try {
            const response = await API.get(`/api/clientes/search?q=${encodeURIComponent(query)}&limit=10`);
            
            if (response.success && response.data.success) {
                this.results = response.data.clientes;
                this.showResults();
            } else {
                this.results = [];
                this.hideResults();
            }
        } catch (error) {
            console.error('Erro ao buscar clientes:', error);
            this.results = [];
            this.hideResults();
        }
    }
    
    showResults() {
        if (this.results.length === 0) {
            this.resultsElement.innerHTML = `
                <div class="autocomplete-item autocomplete-empty">
                    <p>Nenhum cliente encontrado</p>
                    <p class="text-sm text-gray-500">Cadastre um novo cliente</p>
                </div>
            `;
        } else {
            this.resultsElement.innerHTML = this.results.map((cliente, index) => `
                <div class="autocomplete-item" data-index="${index}">
                    <div class="autocomplete-item-content">
                        <strong>${this.escapeHtml(cliente.nome)}</strong>
                        <span class="text-gray-600">${this.formatTelefone(cliente.telefone)}</span>
                    </div>
                    <div class="autocomplete-item-meta">
                        <span class="badge badge-sm">${cliente.total_pedidos || 0} pedidos</span>
                    </div>
                </div>
            `).join('');
            
            // Adicionar event listeners nos itens
            this.resultsElement.querySelectorAll('.autocomplete-item').forEach((item, index) => {
                item.addEventListener('click', () => {
                    this.selectCliente(this.results[index]);
                });
                
                item.addEventListener('mouseenter', () => {
                    this.selectedIndex = index;
                    this.highlightResult();
                });
            });
        }
        
        this.resultsElement.classList.add('active');
        this.selectedIndex = -1;
    }
    
    hideResults() {
        this.resultsElement.classList.remove('active');
        this.resultsElement.innerHTML = '';
        this.selectedIndex = -1;
    }
    
    highlightResult() {
        const items = this.resultsElement.querySelectorAll('.autocomplete-item');
        
        items.forEach((item, index) => {
            if (index === this.selectedIndex) {
                item.classList.add('selected');
            } else {
                item.classList.remove('selected');
            }
        });
    }
    
    selectCliente(cliente) {
        // Preencher input com nome
        this.inputElement.value = cliente.nome;
        
        // Esconder resultados
        this.hideResults();
        
        // Callback para preencher outros campos
        this.onSelect(cliente);
    }
    
    formatTelefone(telefone) {
        if (!telefone) return '';
        
        // Remove tudo que não é número
        const cleaned = telefone.replace(/\D/g, '');
        
        // Formata (11) 99999-9999 ou (11) 9999-9999
        if (cleaned.length === 11) {
            return `(${cleaned.substr(0, 2)}) ${cleaned.substr(2, 5)}-${cleaned.substr(7)}`;
        } else if (cleaned.length === 10) {
            return `(${cleaned.substr(0, 2)}) ${cleaned.substr(2, 4)}-${cleaned.substr(6)}`;
        }
        
        return telefone;
    }
    
    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }
}

// Exportar para uso global
window.AutocompleteCliente = AutocompleteCliente;

