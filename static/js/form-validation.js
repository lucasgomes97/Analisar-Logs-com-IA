/**
 * Form Validation JavaScript
 * Handles client-side form validation and user input sanitization
 * Requirements: 8.2, 8.4 - Form validation and error handling
 */

class FormValidator {
    constructor() {
        this.validators = new Map();
        this.errorMessages = new Map();
        this.init();
    }
    
    init() {
        // Initialize validation rules
        this.setupValidationRules();
        
        // Bind form validation events
        this.bindFormEvents();
        
        console.log('✅ Form validator initialized');
    }
    
    setupValidationRules() {
        // Log analysis form validation
        this.addValidator('log', {
            required: true,
            minLength: 10,
            maxLength: 50000,
            pattern: /[a-zA-Z0-9]/,
            sanitize: true
        });
        
        // Solution editor validation
        this.addValidator('solutionEditor', {
            minLength: 10,
            maxLength: 10000,
            sanitize: true,
            allowEmpty: true
        });
        
        // Classification validation
        this.addValidator('classification', {
            required: true,
            type: 'boolean'
        });
        
        // Analysis ID validation
        this.addValidator('analysisId', {
            required: true,
            pattern: /^[a-zA-Z0-9-_]+$/,
            minLength: 10,
            maxLength: 100
        });
    }
    
    addValidator(fieldName, rules) {
        this.validators.set(fieldName, rules);
    }
    
    bindFormEvents() {
        // Main log form validation
        const logForm = document.getElementById('logForm');
        if (logForm) {
            this.bindFormValidation(logForm);
        }
        
        // Real-time validation for text areas
        const textAreas = document.querySelectorAll('textarea');
        textAreas.forEach(textarea => {
            this.bindTextAreaValidation(textarea);
        });
        
        // Input sanitization on paste
        document.addEventListener('paste', (e) => {
            this.handlePasteEvent(e);
        });
    }
    
    bindFormValidation(form) {
        form.addEventListener('submit', (e) => {
            if (!this.validateForm(form)) {
                e.preventDefault();
                this.showFormErrors(form);
            }
        });
        
        // Real-time validation on input
        const inputs = form.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            input.addEventListener('blur', () => {
                this.validateField(input);
            });
            
            input.addEventListener('input', () => {
                this.clearFieldError(input);
            });
        });
    }
    
    bindTextAreaValidation(textarea) {
        let validationTimeout;
        
        textarea.addEventListener('input', () => {
            clearTimeout(validationTimeout);
            validationTimeout = setTimeout(() => {
                this.validateField(textarea);
            }, 500);
        });
        
        textarea.addEventListener('paste', () => {
            setTimeout(() => {
                this.sanitizeTextArea(textarea);
                this.validateField(textarea);
            }, 100);
        });
    }
    
    validateForm(form) {
        let isValid = true;
        const inputs = form.querySelectorAll('input, textarea, select');
        
        inputs.forEach(input => {
            if (!this.validateField(input)) {
                isValid = false;
            }
        });
        
        return isValid;
    }
    
    validateField(field) {
        const fieldName = field.name || field.id;
        const rules = this.validators.get(fieldName);
        
        if (!rules) {
            return true; // No validation rules defined
        }
        
        const value = field.value.trim();
        const errors = [];
        
        // Required validation
        if (rules.required && !value) {
            errors.push('Este campo é obrigatório');
        }
        
        // Skip other validations if field is empty and not required
        if (!value && !rules.required) {
            this.clearFieldError(field);
            return true;
        }
        
        // Allow empty if explicitly allowed
        if (!value && rules.allowEmpty) {
            this.clearFieldError(field);
            return true;
        }
        
        // Length validations
        if (rules.minLength && value.length < rules.minLength) {
            errors.push(`Mínimo de ${rules.minLength} caracteres`);
        }
        
        if (rules.maxLength && value.length > rules.maxLength) {
            errors.push(`Máximo de ${rules.maxLength} caracteres`);
        }
        
        // Pattern validation
        if (rules.pattern && !rules.pattern.test(value)) {
            errors.push('Formato inválido');
        }
        
        // Type validation
        if (rules.type === 'boolean' && !['true', 'false'].includes(value.toLowerCase())) {
            errors.push('Valor deve ser verdadeiro ou falso');
        }
        
        // Custom validation
        if (rules.custom && typeof rules.custom === 'function') {
            try {
                const customResult = rules.custom(value, field);
                if (customResult !== true) {
                    errors.push(customResult || 'Valor inválido');
                }
            } catch (error) {
                console.error('Error in custom validation:', error);
                errors.push('Erro na validação personalizada');
            }
        }
        
        // Show/hide errors
        if (errors.length > 0) {
            this.showFieldError(field, errors[0]);
            return false;
        } else {
            this.clearFieldError(field);
            return true;
        }
    }
    
    showFieldError(field, message) {
        // Add error class to field
        field.classList.add('field-error');
        
        // Create or update error message
        let errorElement = field.parentNode.querySelector('.field-error-message');
        if (!errorElement) {
            errorElement = document.createElement('div');
            errorElement.className = 'field-error-message';
            field.parentNode.appendChild(errorElement);
        }
        
        errorElement.textContent = message;
        errorElement.style.display = 'block';
        
        // Store error in map
        this.errorMessages.set(field, message);
    }
    
    clearFieldError(field) {
        // Remove error class
        field.classList.remove('field-error');
        
        // Hide error message
        const errorElement = field.parentNode.querySelector('.field-error-message');
        if (errorElement) {
            errorElement.style.display = 'none';
        }
        
        // Remove from error map
        this.errorMessages.delete(field);
    }
    
    showFormErrors(form) {
        const firstErrorField = form.querySelector('.field-error');
        if (firstErrorField) {
            firstErrorField.focus();
            firstErrorField.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        
        // Show general form error
        this.showGeneralError('Por favor, corrija os erros no formulário');
    }
    
    showGeneralError(message) {
        // Create or update general error message
        let errorElement = document.querySelector('.form-general-error');
        if (!errorElement) {
            errorElement = document.createElement('div');
            errorElement.className = 'form-general-error error-message';
            document.body.appendChild(errorElement);
        }
        
        errorElement.textContent = `❌ ${message}`;
        errorElement.style.display = 'block';
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            errorElement.style.display = 'none';
        }, 5000);
    }
    
    sanitizeTextArea(textarea) {
        let value = textarea.value;
        
        // Remove potentially dangerous characters
        value = value.replace(/[<>]/g, '');
        
        // Normalize whitespace
        value = value.replace(/\s+/g, ' ');
        
        // Trim excessive newlines
        value = value.replace(/\n{3,}/g, '\n\n');
        
        // Update textarea if value changed
        if (value !== textarea.value) {
            textarea.value = value;
            this.showFieldWarning(textarea, 'Conteúdo foi sanitizado automaticamente');
        }
    }
    
    showFieldWarning(field, message) {
        // Create warning element
        let warningElement = field.parentNode.querySelector('.field-warning-message');
        if (!warningElement) {
            warningElement = document.createElement('div');
            warningElement.className = 'field-warning-message';
            warningElement.style.color = '#fbbf24';
            warningElement.style.fontSize = '0.8rem';
            warningElement.style.marginTop = '5px';
            field.parentNode.appendChild(warningElement);
        }
        
        warningElement.textContent = `⚠️ ${message}`;
        warningElement.style.display = 'block';
        
        // Auto-hide after 3 seconds
        setTimeout(() => {
            warningElement.style.display = 'none';
        }, 3000);
    }
    
    handlePasteEvent(e) {
        const target = e.target;
        if (target.tagName === 'TEXTAREA' || target.tagName === 'INPUT') {
            setTimeout(() => {
                try {
                    this.sanitizeField(target);
                    this.validateField(target);
                } catch (error) {
                    console.error('Error handling paste event:', error);
                }
            }, 100);
        }
    }
    
    sanitizeField(field) {
        if (field.tagName === 'TEXTAREA') {
            this.sanitizeTextArea(field);
        } else if (field.type === 'text') {
            this.sanitizeTextInput(field);
        }
    }
    
    sanitizeTextInput(input) {
        let value = input.value;
        
        // Remove HTML tags
        value = value.replace(/<[^>]*>/g, '');
        
        // Remove potentially dangerous characters
        value = value.replace(/[<>'"]/g, '');
        
        // Normalize whitespace
        value = value.replace(/\s+/g, ' ').trim();
        
        if (value !== input.value) {
            input.value = value;
            this.showFieldWarning(input, 'Conteúdo foi sanitizado');
        }
    }
    
    // Utility methods
    isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }
    
    isValidURL(url) {
        try {
            new URL(url);
            return true;
        } catch {
            return false;
        }
    }
    
    isValidJSON(str) {
        try {
            JSON.parse(str);
            return true;
        } catch {
            return false;
        }
    }
    
    // Public API methods
    validateAllForms() {
        const forms = document.querySelectorAll('form');
        let allValid = true;
        
        forms.forEach(form => {
            if (!this.validateForm(form)) {
                allValid = false;
            }
        });
        
        return allValid;
    }
    
    addCustomValidator(fieldName, validatorFunction) {
        const existingRules = this.validators.get(fieldName) || {};
        existingRules.custom = validatorFunction;
        this.validators.set(fieldName, existingRules);
    }
    
    removeValidator(fieldName) {
        this.validators.delete(fieldName);
    }
    
    getFieldErrors() {
        const errors = {};
        this.errorMessages.forEach((message, field) => {
            const fieldName = field.name || field.id;
            errors[fieldName] = message;
        });
        return errors;
    }
    
    clearAllErrors() {
        this.errorMessages.forEach((message, field) => {
            this.clearFieldError(field);
        });
    }
    
    // Real-time validation for specific fields
    enableRealTimeValidation(fieldSelector) {
        const fields = document.querySelectorAll(fieldSelector);
        fields.forEach(field => {
            field.addEventListener('input', () => {
                setTimeout(() => this.validateField(field), 300);
            });
        });
    }
    
    // Accessibility improvements
    addAriaLabels() {
        const fields = document.querySelectorAll('input, textarea, select');
        fields.forEach(field => {
            if (!field.getAttribute('aria-label') && !field.getAttribute('aria-labelledby')) {
                const label = field.parentNode.querySelector('label');
                if (label) {
                    const labelId = `label-${field.id || Math.random().toString(36).substr(2, 9)}`;
                    label.id = labelId;
                    field.setAttribute('aria-labelledby', labelId);
                }
            }
        });
    }
}

// Initialize form validator
let formValidator;
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        formValidator = new FormValidator();
    });
} else {
    formValidator = new FormValidator();
}

// Export for global access
window.FormValidator = FormValidator;
window.formValidator = formValidator;