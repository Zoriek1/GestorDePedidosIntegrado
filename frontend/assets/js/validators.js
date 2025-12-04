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
     * Formato esperado: DD/MM/YYYY
     */
    date(value) {
        if (!value) {
            return { valid: false, message: 'Data é obrigatória' };
        }

        // Verificar formato
        if (!/^\d{2}\/\d{2}\/\d{4}$/.test(value)) {
            return {
                valid: false,
                message: 'Data deve estar no formato DD/MM/YYYY'
            };
        }

        // Validar valores
        const [day, month, year] = value.split('/').map(Number);

        if (month < 1 || month > 12) {
            return { valid: false, message: 'Mês inválido' };
        }

        if (day < 1 || day > 31) {
            return { valid: false, message: 'Dia inválido' };
        }

        if (year < 2000 || year > 2100) {
            return { valid: false, message: 'Ano inválido' };
        }

        // Verificar se a data é válida
        const date = new Date(year, month - 1, day);
        if (date.getDate() !== day || date.getMonth() !== month - 1 || date.getFullYear() !== year) {
            return { valid: false, message: 'Data inválida' };
        }

        return { valid: true };
    },

    /**
     * Valida horário
     * Formato esperado: HH:MM
     */
    time(value) {
        if (!value) {
            return { valid: false, message: 'Horário é obrigatório' };
        }

        // Verificar formato
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

