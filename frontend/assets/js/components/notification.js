/**
 * Plante Uma Flor - PWA v3.0
 * Notification Component - Toast notifications
 */

const Notification = {
    container: null,
    duration: 3000,

    /**
     * Inicializa o container de notificações
     */
    init() {
        this.container = document.getElementById('notification-container');
        if (!this.container) {
            console.warn('Container de notificações não encontrado');
        }
    },

    /**
     * Mostra notificação
     * @param {string} message - Mensagem a exibir
     * @param {string} type - Tipo: success, error, warning, info
     * @param {number} duration - Duração em ms (opcional)
     */
    show(message, type = 'info', duration = this.duration) {
        if (!this.container) {
            this.init();
        }

        // Criar elemento da notificação
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        
        // Ícone baseado no tipo
        const icon = this.getIcon(type);
        
        notification.innerHTML = `
            <i class="${icon}"></i>
            <span>${Utils.escapeHtml(message)}</span>
        `;

        // Adicionar ao container
        this.container.appendChild(notification);

        // Remover após duração
        setTimeout(() => {
            this.remove(notification);
        }, duration);

        // Remover ao clicar
        notification.addEventListener('click', () => {
            this.remove(notification);
        });

        return notification;
    },

    /**
     * Retorna ícone baseado no tipo
     */
    getIcon(type) {
        const icons = {
            success: 'fas fa-check-circle',
            error: 'fas fa-times-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };
        return icons[type] || icons.info;
    },

    /**
     * Remove notificação
     */
    remove(notification) {
        if (notification && notification.parentElement) {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(100%)';
            
            setTimeout(() => {
                notification.remove();
            }, 300);
        }
    },

    /**
     * Mostra notificação de sucesso
     */
    success(message, duration) {
        return this.show(message, 'success', duration);
    },

    /**
     * Mostra notificação de erro
     */
    error(message, duration) {
        return this.show(message, 'error', duration);
    },

    /**
     * Mostra notificação de aviso
     */
    warning(message, duration) {
        return this.show(message, 'warning', duration);
    },

    /**
     * Mostra notificação de informação
     */
    info(message, duration) {
        return this.show(message, 'info', duration);
    },

    /**
     * Mostra notificação de loading
     */
    loading(message) {
        const notification = this.show(`${message}...`, 'info', 999999);
        notification.innerHTML = `
            <i class="fas fa-spinner fa-spin"></i>
            <span>${Utils.escapeHtml(message)}...</span>
        `;
        return notification;
    },

    /**
     * Remove todas as notificações
     */
    clearAll() {
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
};

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    Notification.init();
});

