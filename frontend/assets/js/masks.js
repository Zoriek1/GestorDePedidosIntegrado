/**
 * Plante Uma Flor - PWA v3.0
 * Input Masks - Máscaras para campos de entrada
 */

const Masks = {
    /**
     * Aplica máscara de telefone
     * Formato: (XX) XXXXX-XXXX
     */
    phone(input) {
        input.addEventListener('input', (e) => {
            let value = e.target.value.replace(/\D/g, '');
            
            // Limitar a 11 dígitos
            if (value.length > 11) {
                value = value.slice(0, 11);
            }
            
            // Aplicar formato
            if (value.length > 10) {
                value = value.replace(/^(\d{2})(\d{5})(\d{4}).*/, '($1) $2-$3');
            } else if (value.length > 6) {
                value = value.replace(/^(\d{2})(\d{4})(\d{0,4}).*/, '($1) $2-$3');
            } else if (value.length > 2) {
                value = value.replace(/^(\d{2})(\d{0,5})/, '($1) $2');
            } else if (value.length > 0) {
                value = value.replace(/^(\d*)/, '($1');
            }
            
            e.target.value = value;
        });
    },

    /**
     * Aplica máscara de data
     * Formato: DD/MM/YYYY
     */
    date(input) {
        input.addEventListener('input', (e) => {
            let value = e.target.value.replace(/\D/g, '');
            
            // Limitar a 8 dígitos
            if (value.length > 8) {
                value = value.slice(0, 8);
            }
            
            // Aplicar formato
            if (value.length > 4) {
                value = value.replace(/^(\d{2})(\d{2})(\d{0,4})/, '$1/$2/$3');
            } else if (value.length > 2) {
                value = value.replace(/^(\d{2})(\d{0,2})/, '$1/$2');
            }
            
            e.target.value = value;
        });
    },

    /**
     * Aplica máscara de horário
     * Formato: HH:MM
     */
    time(input) {
        input.addEventListener('input', (e) => {
            let value = e.target.value.replace(/\D/g, '');
            
            // Limitar a 4 dígitos
            if (value.length > 4) {
                value = value.slice(0, 4);
            }
            
            // Aplicar formato
            if (value.length > 2) {
                value = value.replace(/^(\d{2})(\d{0,2})/, '$1:$2');
            }
            
            e.target.value = value;
        });

        // Validar valores ao sair do campo
        input.addEventListener('blur', (e) => {
            const value = e.target.value;
            if (value.length === 5) {
                const [hours, minutes] = value.split(':').map(Number);
                
                // Corrigir horas inválidas
                if (hours > 23) {
                    e.target.value = `23:${minutes.toString().padStart(2, '0')}`;
                }
                
                // Corrigir minutos inválidos
                if (minutes > 59) {
                    e.target.value = `${hours.toString().padStart(2, '0')}:59`;
                }
            }
        });
    },

    /**
     * Aplica máscara de CEP
     * Formato: XXXXX-XXX
     */
    cep(input) {
        input.addEventListener('input', (e) => {
            let value = e.target.value.replace(/\D/g, '');
            
            // Limitar a 8 dígitos
            if (value.length > 8) {
                value = value.slice(0, 8);
            }
            
            // Aplicar formato
            if (value.length > 5) {
                value = value.replace(/^(\d{5})(\d{0,3})/, '$1-$2');
            }
            
            e.target.value = value;
        });
    },

    /**
     * Remove máscara de CEP
     */
    unmaskCep(value) {
        return value ? value.replace(/\D/g, '') : '';
    },

    /**
     * Aplica máscara de moeda
     * Formato: R$ X.XXX,XX
     */
    currency(input) {
        let value = '';

        input.addEventListener('input', (e) => {
            // Remove tudo exceto dígitos
            let inputValue = e.target.value.replace(/\D/g, '');
            
            if (!inputValue) {
                e.target.value = '';
                return;
            }

            // Converte para centavos
            const amount = parseInt(inputValue, 10) / 100;
            
            // Formata para moeda brasileira
            e.target.value = new Intl.NumberFormat('pt-BR', {
                style: 'currency',
                currency: 'BRL'
            }).format(amount);
        });
    },

    /**
     * Remove máscara de telefone
     */
    unmaskPhone(value) {
        return value ? value.replace(/\D/g, '') : '';
    },

    /**
     * Remove máscara de data
     */
    unmaskDate(value) {
        if (!value) return '';
        
        // Se está no formato DD/MM/YYYY, converter para YYYY-MM-DD
        if (/^\d{2}\/\d{2}\/\d{4}$/.test(value)) {
            const [day, month, year] = value.split('/');
            return `${year}-${month}-${day}`;
        }
        
        return value;
    },

    /**
     * Remove máscara de horário
     * Preserva formato de intervalo "HH:MM - HH:MM"
     */
    unmaskTime(value) {
        if (!value) return '';
        // Se for intervalo (contém ' - '), preservar formato completo
        if (value.includes(' - ')) {
            return value.trim();
        }
        // Horário simples: remover caracteres inválidos
        return value.replace(/[^\d:]/g, '');
    },

    /**
     * Remove máscara de moeda
     */
    unmaskCurrency(value) {
        if (!value) return '';
        
        // Remove R$, pontos e substitui vírgula por ponto
        return value
            .replace('R$', '')
            .replace(/\./g, '')
            .replace(',', '.')
            .trim();
    },

    /**
     * Aplica todas as máscaras automaticamente
     */
    applyAll() {
        // Telefone
        document.querySelectorAll('[data-mask="phone"]').forEach(input => {
            this.phone(input);
        });

        // Data
        document.querySelectorAll('[data-mask="date"]').forEach(input => {
            this.date(input);
        });

        // Horário
        document.querySelectorAll('[data-mask="time"]').forEach(input => {
            this.time(input);
        });

        // CEP
        document.querySelectorAll('[data-mask="cep"]').forEach(input => {
            this.cep(input);
        });

        // Moeda
        document.querySelectorAll('[data-mask="currency"]').forEach(input => {
            this.currency(input);
        });
    },

    /**
     * Permite apenas números
     */
    numbersOnly(input) {
        input.addEventListener('input', (e) => {
            e.target.value = e.target.value.replace(/\D/g, '');
        });
    },

    /**
     * Permite apenas letras
     */
    lettersOnly(input) {
        input.addEventListener('input', (e) => {
            e.target.value = e.target.value.replace(/[^a-zA-ZÀ-ÿ\s]/g, '');
        });
    }
};

// Auto-aplicar máscaras quando o DOM carregar
document.addEventListener('DOMContentLoaded', () => {
    Masks.applyAll();
});

// Observar mudanças no DOM para aplicar máscaras em elementos dinâmicos
const observer = new MutationObserver(() => {
    Masks.applyAll();
});

observer.observe(document.body, {
    childList: true,
    subtree: true
});

