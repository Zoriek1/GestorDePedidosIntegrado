/**
 * Plante Uma Flor - PWA v3.0
 * Modal Component - Modais de confirmação e diálogo
 */

const Modal = {
    currentModal: null,

    /**
     * Mostra modal de confirmação
     * @param {Object} options - Opções do modal
     * @returns {Promise} Resolve com true se confirmado, false se cancelado
     */
    confirm(options = {}) {
        const {
            title = 'Confirmar',
            message = 'Tem certeza?',
            confirmText = 'Confirmar',
            cancelText = 'Cancelar',
            confirmClass = 'btn-danger',
            icon = 'fa-question-circle'
        } = options;

        return new Promise((resolve) => {
            const modal = this.create({
                title,
                message,
                icon,
                buttons: [
                    {
                        text: cancelText,
                        class: 'btn-secondary',
                        onClick: () => {
                            this.close(modal);
                            resolve(false);
                        }
                    },
                    {
                        text: confirmText,
                        class: confirmClass,
                        onClick: () => {
                            this.close(modal);
                            resolve(true);
                        }
                    }
                ]
            });

            this.show(modal);
        });
    },

    /**
     * Mostra modal de alerta
     */
    alert(options = {}) {
        const {
            title = 'Atenção',
            message = '',
            okText = 'OK',
            icon = 'fa-info-circle'
        } = options;

        return new Promise((resolve) => {
            const modal = this.create({
                title,
                message,
                icon,
                buttons: [
                    {
                        text: okText,
                        class: 'btn-primary',
                        onClick: () => {
                            this.close(modal);
                            resolve(true);
                        }
                    }
                ]
            });

            this.show(modal);
        });
    },

    /**
     * Cria estrutura do modal usando Shoelace Dialog
     */
    create(options) {
        const {
            title,
            message,
            icon,
            buttons = []
        } = options;

        const dialog = document.createElement('sl-dialog');
        dialog.label = title || 'Dialog';
        dialog.noHeader = !title;

        if (icon) {
            const iconEl = document.createElement('sl-icon');
            iconEl.name = icon.replace('fa-', '');
            iconEl.library = 'fa';
            iconEl.style.fontSize = '3rem';
            iconEl.style.color = 'var(--color-primary)';
            iconEl.style.marginBottom = 'var(--spacing-4)';
            dialog.appendChild(iconEl);
        }

        if (message) {
            const messageEl = document.createElement('p');
            messageEl.textContent = message;
            messageEl.className = 'text-gray-600 mb-6';
            dialog.appendChild(messageEl);
        }

        const buttonsContainer = document.createElement('div');
        buttonsContainer.className = 'flex gap-3 justify-end';
        buttonsContainer.slot = 'footer';

        buttons.forEach(btn => {
            const variant = btn.class.includes('primary')
                ? 'primary'
                : btn.class.includes('danger')
                    ? 'danger'
                    : btn.class.includes('success')
                        ? 'success'
                        : 'default';

            const slButton = Utils.createSlButton({
                variant,
                text: btn.text,
                onclick: () => {
                    btn.onClick();
                    dialog.hide();
                }
            });

            buttonsContainer.appendChild(slButton);
        });

        dialog.appendChild(buttonsContainer);
        document.body.appendChild(dialog);

        return dialog;
    },

    /**
     * Mostra modal
     * Aceita: Node, string HTML, array de Nodes, ou (title, content) para compatibilidade
     */
    show(modal, content) {
        // Sobrecarga: se content for fornecido, tratar como (title, content)
        if (content !== undefined) {
            const title = modal;
            const modalElement = this.custom(content, null);
            // Se o modal tiver header, podemos atualizar o label
            if (modalElement.tagName === 'SL-DIALOG' && title) {
                modalElement.label = title;
            }
            return;
        }

        if (!modal) return;

        // Função helper para converter qualquer coisa para Node
        const toNode = (input) => {
            // Se já é Node, retornar
            if (input instanceof Node) {
                return input;
            }

            // Se é array, agregar em DocumentFragment
            if (Array.isArray(input)) {
                const fragment = document.createDocumentFragment();
                input.forEach(item => {
                    const node = toNode(item);
                    if (node) fragment.appendChild(node);
                });
                return fragment;
            }

            // Se é string, usar template para converter HTML
            if (typeof input === 'string') {
                const template = document.createElement('template');
                template.innerHTML = input.trim();
                // Se template tem um único elemento filho, retornar ele; senão retornar fragment
                return template.content.childNodes.length === 1 
                    ? template.content.firstChild 
                    : template.content;
            }

            // Fallback: converter para TextNode
            return document.createTextNode(String(input || ''));
        };

        const modalNode = toNode(modal);

        if (modalNode.tagName === 'SL-DIALOG') {
            const doShow = () => {
                if (typeof modalNode.show === 'function') {
                    modalNode.show();
                } else {
                    modalNode.setAttribute('open', '');
                }
            };
            requestAnimationFrame(doShow);
            this.currentModal = modalNode;
        } else {
            // Se modalNode é DocumentFragment, criar container
            let container = modalNode;
            if (modalNode instanceof DocumentFragment) {
                container = document.createElement('div');
                container.className = 'modal-content';
                container.appendChild(modalNode);
            }
            
            document.body.appendChild(container);
            this.currentModal = container;
            setTimeout(() => {
                container.classList.add('active');
            }, 10);
        }
    },

    /**
     * Fecha modal
     */
    close(modal) {
        if (!modal) modal = this.currentModal;
        if (!modal) return;

        if (modal.tagName === 'SL-DIALOG') {
            modal.hide();
            setTimeout(() => {
                if (modal.parentNode) modal.parentNode.removeChild(modal);
            }, 300);
            this.currentModal = null;
            return;
        }

        modal.classList.remove('active');
        setTimeout(() => {
            modal.remove();
            if (this.currentModal === modal) {
                this.currentModal = null;
            }
        }, 200);
    },

    /**
     * Modal de confirmação de deleção
     */
    confirmDelete(itemName = 'este item') {
        return this.confirm({
            title: 'Confirmar Exclusão',
            message: `Tem certeza que deseja deletar ${itemName}? Esta ação não pode ser desfeita.`,
            confirmText: 'Deletar',
            cancelText: 'Cancelar',
            confirmClass: 'btn-danger',
            icon: 'fa-trash-alt'
        });
    },

    /**
     * Modal customizado com HTML usando Shoelace Dialog
     */
    custom(htmlContent, onClose) {
        const dialog = document.createElement('sl-dialog');
        dialog.noHeader = true;
        dialog.innerHTML = htmlContent;
        
        // OCULTAR ANTES DE ANEXAR - prevenir glitch visual
        dialog.style.opacity = '0';
        dialog.style.visibility = 'hidden';
        dialog.style.position = 'fixed'; // Forçar fixed desde o início

        // Fechar ao esconder
        dialog.addEventListener('sl-after-hide', () => {
            if (dialog.parentNode) dialog.parentNode.removeChild(dialog);
            if (onClose) onClose();
            if (this.currentModal === dialog) this.currentModal = null;
        });

        // Botões com data-modal-close
        const bindCloseButtons = () => {
            dialog.querySelectorAll('[data-modal-close]').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    dialog.hide();
                });
            });
        };

        // Anexar ao body (ainda oculto)
        document.body.appendChild(dialog);
        setTimeout(bindCloseButtons, 0);

        const openDialog = () => {
            // Aguardar próximo frame para garantir renderização
            requestAnimationFrame(() => {
                // Garantir que está posicionado corretamente
                if (dialog.shadowRoot) {
                    const panel = dialog.shadowRoot.querySelector('[part="panel"]');
                    if (panel) {
                        // Forçar centralização
                        panel.style.margin = 'auto';
                    }
                }
                
                // Remover ocultação e mostrar
                dialog.style.opacity = '';
                dialog.style.visibility = '';
                
                // Chamar show do Shoelace
                if (typeof dialog.show === 'function') {
                    dialog.show();
                } else {
                    dialog.setAttribute('open', '');
                }
            });
        };

        if (customElements && typeof customElements.whenDefined === 'function') {
            customElements.whenDefined('sl-dialog').then(() => {
                // Aguardar mais um frame após definição
                requestAnimationFrame(openDialog);
            });
        } else {
            // Fallback: aguardar um pouco mais
            setTimeout(openDialog, 50);
        }
        
        this.currentModal = dialog;
        return dialog;
    }
};

