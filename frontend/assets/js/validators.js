/**
 * Plante Uma Flor - PWA v3.0
 * Validators - Validação de campos do formulário
 */

const Validators = {
    /**
     * Valida se campo não está vazio
     */
    required(value, fieldName = 'Campo') {
        if (!value || value.trim() === '') {
            return {
                valid: false,
                message: `${fieldName} é obrigatório`
            };
        }
        return { valid: true };
    },

    /**
     * Valida telefone
     * Formato esperado: (XX) XXXXX-XXXX ou (XX) XXXX-XXXX
     */
    phone(value) {
        if (!value) {
            return { valid: false, message: 'Telefone é obrigatório' };
        }

        const cleaned = value.replace(/\D/g, '');
        
        if (cleaned.length < 10 || cleaned.length > 11) {
            return {
                valid: false,
                message: 'Telefone deve ter 10 ou 11 dígitos'
            };
        }

        return { valid: true };
    },

    /**
     * Valida data
     * Aceita qualquer formato válido de data
     */
    date(value) {
        if (!value) {
            return { valid: false, message: 'Data é obrigatória' };
        }

        // Tentar criar objeto Date a partir do valor
        let dateObj;
        
        // Tentar formato DD/MM/YYYY
        if (/^\d{2}\/\d{2}\/\d{4}$/.test(value)) {
            const [day, month, year] = value.split('/').map(Number);
            dateObj = new Date(year, month - 1, day);
            
            // Verificar se a data é válida
            if (dateObj.getDate() !== day || dateObj.getMonth() !== month - 1 || dateObj.getFullYear() !== year) {
                return { valid: false, message: 'Data inválida' };
            }
        } 
        // Tentar formato YYYY-MM-DD
        else if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
            dateObj = new Date(value + 'T00:00:00');
            if (isNaN(dateObj.getTime())) {
                return { valid: false, message: 'Data inválida' };
            }
        }
        // Tentar parse direto
        else {
            dateObj = new Date(value);
            if (isNaN(dateObj.getTime())) {
                return { valid: false, message: 'Data inválida' };
            }
        }

        // Validar se a data está em um range razoável
        const year = dateObj.getFullYear();
        if (year < 2000 || year > 2100) {
            return { valid: false, message: 'Ano inválido' };
        }

        return { valid: true };
    },

    /**
     * Valida horário
     * Formato esperado: HH:MM ou HH:MM - HH:MM (intervalo)
     */
    time(value) {
        if (!value) {
            return { valid: false, message: 'Horário é obrigatório' };
        }

        // Verificar se é intervalo
        const isIntervalo = value.includes(' - ');
        
        if (isIntervalo) {
            // Validar formato de intervalo: HH:MM - HH:MM
            const partes = value.split(' - ');
            if (partes.length !== 2) {
                return {
                    valid: false,
                    message: 'Intervalo deve estar no formato HH:MM - HH:MM'
                };
            }

            const [horarioInicial, horarioFinal] = partes;
            
            // Validar horário inicial
            if (!/^\d{2}:\d{2}$/.test(horarioInicial.trim())) {
                return {
                    valid: false,
                    message: 'Horário inicial deve estar no formato HH:MM'
                };
            }

            // Validar horário final
            if (!/^\d{2}:\d{2}$/.test(horarioFinal.trim())) {
                return {
                    valid: false,
                    message: 'Horário final deve estar no formato HH:MM'
                };
            }

            // Validar valores do horário inicial
            const [h1, m1] = horarioInicial.trim().split(':').map(Number);
            if (h1 < 0 || h1 > 23) {
                return { valid: false, message: 'Hora inicial inválida (00-23)' };
            }
            if (m1 < 0 || m1 > 59) {
                return { valid: false, message: 'Minutos iniciais inválidos (00-59)' };
            }

            // Validar valores do horário final
            const [h2, m2] = horarioFinal.trim().split(':').map(Number);
            if (h2 < 0 || h2 > 23) {
                return { valid: false, message: 'Hora final inválida (00-23)' };
            }
            if (m2 < 0 || m2 > 59) {
                return { valid: false, message: 'Minutos finais inválidos (00-59)' };
            }

            // Validar que horário final é depois do inicial
            const minutosInicial = h1 * 60 + m1;
            const minutosFinal = h2 * 60 + m2;
            if (minutosFinal <= minutosInicial) {
                return { valid: false, message: 'O horário final deve ser depois do horário inicial' };
            }

            return { valid: true };
        } else {
            // Validar formato de horário específico: HH:MM
            if (!/^\d{2}:\d{2}$/.test(value)) {
                return {
                    valid: false,
                    message: 'Horário deve estar no formato HH:MM'
                };
            }

            // Validar valores
            const [hours, minutes] = value.split(':').map(Number);

            if (hours < 0 || hours > 23) {
                return { valid: false, message: 'Hora inválida (00-23)' };
            }

            if (minutes < 0 || minutes > 59) {
                return { valid: false, message: 'Minutos inválidos (00-59)' };
            }

            return { valid: true };
        }
    },

    /**
     * Valida valor monetário
     */
    currency(value) {
        if (!value) {
            return { valid: true }; // Valor é opcional
        }

        // Remove formatação
        const cleaned = value.replace(/[^\d,.-]/g, '');
        
        if (cleaned === '') {
            return { valid: true };
        }

        // Converte para número
        const amount = parseFloat(cleaned.replace(',', '.'));

        if (isNaN(amount) || amount < 0) {
            return { valid: false, message: 'Valor inválido' };
        }

        return { valid: true };
    },

    /**
     * Valida email
     */
    email(value) {
        if (!value) {
            return { valid: true }; // Email é opcional
        }

        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        
        if (!emailRegex.test(value)) {
            return { valid: false, message: 'Email inválido' };
        }

        return { valid: true };
    },

    /**
     * Valida tamanho mínimo
     */
    minLength(value, min, fieldName = 'Campo') {
        if (!value || value.length < min) {
            return {
                valid: false,
                message: `${fieldName} deve ter no mínimo ${min} caracteres`
            };
        }
        return { valid: true };
    },

    /**
     * Valida tamanho máximo
     */
    maxLength(value, max, fieldName = 'Campo') {
        if (value && value.length > max) {
            return {
                valid: false,
                message: `${fieldName} deve ter no máximo ${max} caracteres`
            };
        }
        return { valid: true };
    },

    /**
     * Valida campo do formulário e mostra feedback visual
     */
    validateField(input, validationType, fieldName) {
        const value = input.value;
        let result;

        switch (validationType) {
            case 'required':
                result = this.required(value, fieldName);
                break;
            case 'phone':
                result = this.phone(value);
                break;
            case 'date':
                result = this.date(value);
                break;
            case 'time':
                result = this.time(value);
                break;
            case 'currency':
                result = this.currency(value);
                break;
            case 'email':
                result = this.email(value);
                break;
            default:
                result = { valid: true };
        }

        // Atualizar feedback visual
        this.updateFieldFeedback(input, result);

        return result;
    },

    /**
     * Atualiza feedback visual do campo
     */
    updateFieldFeedback(input, result) {
        // Remove classes anteriores
        input.classList.remove('border-red-500', 'border-primary');

        // Remove mensagem de erro anterior
        const existingError = input.parentElement.querySelector('.field-error');
        if (existingError) {
            existingError.remove();
        }

        if (!result.valid) {
            // Adiciona borda vermelha
            input.classList.add('border-red-500');

            // Adiciona mensagem de erro
            const errorMsg = document.createElement('p');
            errorMsg.className = 'field-error text-red-500 text-sm mt-1';
            errorMsg.textContent = result.message;
            input.parentElement.appendChild(errorMsg);
        } else if (input.value.trim() !== '') {
            // Adiciona borda verde para campo válido preenchido
            input.classList.add('border-primary');
        }
    },

    /**
     * Valida todos os campos obrigatórios de um formulário
     */
    validateForm(formElement) {
        let isValid = true;
        const errors = [];

        // Validar campos obrigatórios
        const requiredFields = formElement.querySelectorAll('[required]');
        
        requiredFields.forEach(field => {
            const fieldName = field.getAttribute('data-field-name') || field.name || 'Campo';
            const validationType = field.getAttribute('data-validation') || 'required';
            
            const result = this.validateField(field, validationType, fieldName);
            
            if (!result.valid) {
                isValid = false;
                errors.push({
                    field: field.name || field.id,
                    message: result.message
                });
            }
        });

        return { valid: isValid, errors };
    },

    /**
     * Remove feedback de erro de um campo
     */
    clearFieldError(input) {
        input.classList.remove('border-red-500', 'border-primary');
        
        const errorMsg = input.parentElement.querySelector('.field-error');
        if (errorMsg) {
            errorMsg.remove();
        }
    },

    /**
     * Configura validação em tempo real
     */
    setupRealTimeValidation(input, validationType, fieldName) {
        // Validar ao sair do campo
        input.addEventListener('blur', () => {
            if (input.value.trim() !== '') {
                this.validateField(input, validationType, fieldName);
            }
        });

        // Limpar erro ao focar
        input.addEventListener('focus', () => {
            this.clearFieldError(input);
        });
    }
};

// Auto-configurar validação em tempo real para campos com data-validation
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-validation]').forEach(input => {
        const validationType = input.getAttribute('data-validation');
        const fieldName = input.getAttribute('data-field-name') || input.name || 'Campo';
        Validators.setupRealTimeValidation(input, validationType, fieldName);
    });
});

// Observar mudanças no DOM para configurar validação em elementos dinâmicos
const validatorObserver = new MutationObserver(() => {
    document.querySelectorAll('[data-validation]').forEach(input => {
        if (!input.dataset.validationConfigured) {
            const validationType = input.getAttribute('data-validation');
            const fieldName = input.getAttribute('data-field-name') || input.name || 'Campo';
            Validators.setupRealTimeValidation(input, validationType, fieldName);
            input.dataset.validationConfigured = 'true';
        }
    });
});

validatorObserver.observe(document.body, {
    childList: true,
    subtree: true
});

