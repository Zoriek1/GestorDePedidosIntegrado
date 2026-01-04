/**
 * Componente Autocomplete de Clientes
 * Busca clientes em tempo real e permite seleção para preenchimento automático
 * @deprecated Use Awesomplete no lugar deste componente. Será removido após migração.
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
        
        // Detectar mobile
        this.isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) || window.innerWidth <= 768;
        
        // Event listeners
        this.inputElement.addEventListener('input', (e) => this.handleInput(e));
        this.inputElement.addEventListener('keydown', (e) => this.handleKeydown(e));
        this.inputElement.addEventListener('focus', () => {
            if (this.inputElement.value.length >= 2) {
                this.search(this.inputElement.value);
            }
        });
        
        // Fechar ao clicar/tocar fora (suporte mobile)
        const handleOutsideClick = (e) => {
            if (!this.inputElement.contains(e.target) && !this.resultsElement.contains(e.target)) {
                this.hideResults();
            }
        };
        document.addEventListener('click', handleOutsideClick);
        // Adicionar touchstart para mobile
        if (this.isMobile) {
            document.addEventListener('touchstart', handleOutsideClick, { passive: true });
        }
        
        // Prevenir scroll do body quando autocomplete está aberto (mobile)
        this.resultsElement.addEventListener('touchmove', (e) => {
            e.stopPropagation();
        }, { passive: false });
        
        // Fechar dropdown ao scrollar (mobile)
        if (this.isMobile) {
            this.scrollHandler = () => {
                if (this.resultsElement.classList.contains('active')) {
                    this.hideResults();
                }
            };
            window.addEventListener('scroll', this.scrollHandler, { passive: true });
        }
    }
    
    handleInput(e) {
        const query = e.target.value.trim();
        
        // Limpar timeout anterior
        if (this.debounceTimeout) {
            clearTimeout(this.debounceTimeout);
        }
        
        // Buscar após debounce - maior delay no mobile para melhor performance
        const debounceDelay = this.isMobile ? 400 : 300;
        if (query.length >= 2) {
            this.debounceTimeout = setTimeout(() => {
                this.search(query);
            }, debounceDelay);
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
                <div class="autocomplete-item" data-index="${index}" role="option" tabindex="0">
                    <div class="autocomplete-item-content">
                        <strong>${this.escapeHtml(cliente.nome)}</strong>
                        <span class="text-gray-600">${this.formatTelefone(cliente.telefone)}</span>
                    </div>
                    <div class="autocomplete-item-meta">
                        <span class="badge badge-sm">${cliente.total_pedidos || 0} pedidos</span>
                    </div>
                </div>
            `).join('');
            
            // Adicionar event listeners nos itens (suporte mobile e desktop)
            this.resultsElement.querySelectorAll('.autocomplete-item').forEach((item, index) => {
                const selectHandler = (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    this.selectCliente(this.results[index]);
                };
                
                // Click para desktop
                item.addEventListener('click', selectHandler);
                
                // Touchstart para mobile (mais confiável que click)
                item.addEventListener('touchstart', (e) => {
                    e.preventDefault();
                    selectHandler(e);
                }, { passive: false });
                
                // Suporte a keyboard
                item.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                        selectHandler(e);
                    }
                });
                
                // Hover apenas no desktop
                if (!this.isMobile) {
                    item.addEventListener('mouseenter', () => {
                        this.selectedIndex = index;
                        this.highlightResult();
                    });
                }
            });
        }
        
        // Configurar atributos de acessibilidade
        this.resultsElement.setAttribute('role', 'listbox');
        this.inputElement.setAttribute('aria-expanded', 'true');
        this.inputElement.setAttribute('aria-controls', this.resultsElement.id || 'autocomplete-results');
        
        // No mobile, recalcular posição se necessário
        if (this.isMobile) {
            this.adjustMobilePosition();
        }
        
        this.resultsElement.classList.add('active');
        this.selectedIndex = -1;
    }
    
    adjustMobilePosition() {
        // Calcular posição do input para ajustar dropdown no mobile
        const inputRect = this.inputElement.getBoundingClientRect();
        const viewportHeight = window.innerHeight;
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        
        // Calcular posição top usando position fixed (coordenadas relativas à viewport)
        // No mobile, usar position fixed com coordenadas da viewport
        const topPosition = inputRect.bottom + 4; // 4px = margin-top, coordenadas da viewport
        
        // Aplicar posição
        this.resultsElement.style.top = topPosition + 'px';
        this.resultsElement.style.position = 'fixed';
        
        // Calcular espaço disponível abaixo do input
        const spaceBelow = viewportHeight - inputRect.bottom;
        const maxHeight = Math.min(250, spaceBelow - 20); // 20px de margem
        
        // Ajustar max-height se necessário
        if (maxHeight < 100) {
            this.resultsElement.style.maxHeight = '100px';
        } else {
            this.resultsElement.style.maxHeight = maxHeight + 'px';
        }
        
        // Garantir z-index alto e outros estilos
        this.resultsElement.style.zIndex = '9999';
        this.resultsElement.style.visibility = 'visible';
        this.resultsElement.style.left = inputRect.left + 8 + 'px'; // 8px = 0.5rem margin
        this.resultsElement.style.width = (inputRect.width - 16) + 'px'; // 16px = 0.5rem * 2 (margens)
    }
    
    hideResults() {
        this.resultsElement.classList.remove('active');
        this.resultsElement.innerHTML = '';
        this.selectedIndex = -1;
        
        // Resetar estilos inline do mobile
        if (this.isMobile) {
            this.resultsElement.style.top = '';
            this.resultsElement.style.left = '';
            this.resultsElement.style.width = '';
        }
        
        // Atualizar atributos de acessibilidade
        if (this.inputElement) {
            this.inputElement.setAttribute('aria-expanded', 'false');
        }
    }
    
    // Cleanup ao destruir instância
    destroy() {
        if (this.scrollHandler) {
            window.removeEventListener('scroll', this.scrollHandler);
        }
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

