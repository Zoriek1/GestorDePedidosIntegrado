/**
 * Plante Uma Flor - PWA v3.0
 * Utilitários gerais
 */

const Utils = {
    /**
     * Mostra loading overlay
     */
    showLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.remove('hidden');
        }
    },

    /**
     * Esconde loading overlay
     */
    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.add('hidden');
        }
    },

    /**
     * Formata data para exibição (DD/MM/YYYY)
     */
    formatDate(dateString) {
        if (!dateString) return '';
        
        try {
            const date = new Date(dateString + 'T00:00:00');
            const day = String(date.getDate()).padStart(2, '0');
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const year = date.getFullYear();
            return `${day}/${month}/${year}`;
        } catch (error) {
            return dateString;
        }
    },

    /**
     * Formata data para envio à API (YYYY-MM-DD)
     */
    formatDateForAPI(dateString) {
        if (!dateString) return '';
        
        // Se já está no formato YYYY-MM-DD
        if (/^\d{4}-\d{2}-\d{2}$/.test(dateString)) {
            return dateString;
        }
        
        // Se está no formato DD/MM/YYYY
        if (/^\d{2}\/\d{2}\/\d{4}$/.test(dateString)) {
            const [day, month, year] = dateString.split('/');
            return `${year}-${month}-${day}`;
        }
        
        return dateString;
    },

    /**
     * Formata horário (HH:MM)
     */
    formatTime(timeString) {
        if (!timeString) return '';
        return timeString.substring(0, 5);
    },

    /**
     * Formata telefone para exibição
     */
    formatPhone(phone) {
        if (!phone) return '';
        const cleaned = phone.replace(/\D/g, '');
        
        if (cleaned.length === 11) {
            return `(${cleaned.substring(0, 2)}) ${cleaned.substring(2, 7)}-${cleaned.substring(7)}`;
        }
        
        return phone;
    },

    /**
     * Formata valor monetário
     */
    formatCurrency(value) {
        if (!value) return '';
        
        // Remove tudo exceto dígitos
        const cleaned = value.toString().replace(/\D/g, '');
        
        if (!cleaned) return '';
        
        // Converte para centavos
        const amount = parseFloat(cleaned) / 100;
        
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(amount);
    },

    /**
     * Debounce para otimizar buscas
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    /**
     * Traduz status para texto legível
     */
    translateStatus(status) {
        const translations = {
            'agendado': 'Agendado',
            'em_producao': 'Em Produção',
            'pronto_entrega': 'Pronto para Entrega',
            'em_rota': 'Em Rota',
            'pronto_retirada': 'Pronto para Retirada',
            'concluido': 'Concluído'
        };
        
        return translations[status] || status;
    },

    /**
     * Traduz tipo de pedido
     */
    translateType(type) {
        const translations = {
            'Entrega': 'Entrega',
            'Retirada': 'Retirada'
        };
        
        return translations[type] || type;
    },

    /**
     * Copia texto para clipboard
     */
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            Notification.show('Copiado para área de transferência', 'success');
            return true;
        } catch (error) {
            console.error('Erro ao copiar:', error);
            return false;
        }
    },

    /**
     * Verifica se está online
     */
    isOnline() {
        return navigator.onLine;
    },

    /**
     * Scroll suave para elemento
     */
    scrollToElement(element) {
        if (element) {
            element.scrollIntoView({
                behavior: 'smooth',
                block: 'center'
            });
        }
    },

    /**
     * Gera ID único
     */
    generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    },

    /**
     * Sanitiza HTML para prevenir XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * Formata texto longo com reticências
     */
    truncate(text, maxLength = 100) {
        if (!text || text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    },

    /**
     * Valida se data é futura
     */
    isFutureDate(dateString) {
        const date = new Date(dateString);
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        return date >= today;
    },

    /**
     * Calcula dias até a data
     */
    daysUntil(dateString) {
        const date = new Date(dateString);
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const diff = date - today;
        return Math.ceil(diff / (1000 * 60 * 60 * 24));
    },

    /**
     * Cria um botão Shoelace configurado
     * @param {Object} options - { variant, size, text, icon, onclick, disabled, loading, className }
     * @returns {HTMLElement} sl-button
     */
    createSlButton(options = {}) {
        const {
            variant = 'default', // 'default', 'primary', 'success', 'warning', 'danger', 'text'
            size = 'medium', // 'small', 'medium', 'large'
            text = '',
            icon = null, // { name: 'plus-circle', slot: 'prefix' | 'suffix', library: 'fa' }
            onclick = null,
            disabled = false,
            loading = false,
            className = ''
        } = options;

        const button = document.createElement('sl-button');
        button.variant = variant;
        button.size = size;
        button.disabled = disabled;
        button.loading = loading;
        if (className) button.className = className;
        if (text) button.appendChild(document.createTextNode(text));

        if (icon) {
            const iconEl = document.createElement('sl-icon');
            iconEl.name = icon.name;
            iconEl.slot = icon.slot || 'prefix';
            iconEl.library = icon.library || 'fa';
            button.appendChild(iconEl);
        }

        if (onclick) {
            button.addEventListener('click', onclick);
        }

        return button;
    }
};

// Listener para mudanças de status online/offline
window.addEventListener('online', () => {
    Notification.show('Conexão restaurada', 'success');
});

window.addEventListener('offline', () => {
    Notification.show('Você está offline. Alterações serão sincronizadas quando voltar online.', 'warning');
});

