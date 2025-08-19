/**
 * Feedback Interface JavaScript
 * Handles solution classification, editing, and AJAX interactions
 * Requirements: 1.1, 1.2, 2.1, 2.2, 8.1, 8.2, 8.3, 8.4
 */

class FeedbackManager {
    constructor() {
        this.solutionEditor = null;
        this.btnValid = null;
        this.btnInvalid = null;
        this.btnSave = null;
        this.feedbackStatus = null;
        this.analysisId = null;
        
        // State variables
        this.selectedClassification = null;
        this.originalSolution = '';
        this.hasChanges = false;
        this.isLoading = false;
        
        this.init();
    }
    
    init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initializeElements());
        } else {
            this.initializeElements();
        }
    }
    
    initializeElements() {
        // Get feedback elements
        this.solutionEditor = document.getElementById('solutionEditor');
        this.btnValid = document.getElementById('btnValid');
        this.btnInvalid = document.getElementById('btnInvalid');
        this.btnSave = document.getElementById('btnSave');
        this.feedbackStatus = document.getElementById('feedbackStatus');
        this.analysisId = document.getElementById('analysisId');
        
        // Check if feedback elements exist (only when there's an analysis result)
        if (!this.solutionEditor || !this.btnValid || !this.btnInvalid || !this.btnSave || !this.analysisId) {
            return; // Exit if feedback elements don't exist
        }
        
        // Initialize state
        this.originalSolution = this.solutionEditor.value;
        
        // Bind event listeners
        this.bindEvents();
        
        // Initial state update
        this.updateSaveButtonState();
        
        console.log('✅ Feedback manager initialized');
    }
    
    bindEvents() {
        // Track solution changes with debouncing
        let changeTimeout;
        this.solutionEditor.addEventListener('input', () => {
            clearTimeout(changeTimeout);
            changeTimeout = setTimeout(() => this.handleSolutionChange(), 300);
        });
        
        // Classification button handlers
        this.btnValid.addEventListener('click', () => this.selectClassification('valid'));
        this.btnInvalid.addEventListener('click', () => this.selectClassification('invalid'));
        
        // Save button handler
        this.btnSave.addEventListener('click', () => this.saveFeedback());
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboardShortcuts(e));
        
        // Form validation on paste
        this.solutionEditor.addEventListener('paste', () => {
            setTimeout(() => this.validateSolutionContent(), 100);
        });
    }
    
    handleSolutionChange() {
        const currentValue = this.solutionEditor.value.trim();
        const originalValue = this.originalSolution.trim();
        
        if (currentValue !== originalValue) {
            this.solutionEditor.classList.add('solution-changed');
            this.hasChanges = true;
        } else {
            this.solutionEditor.classList.remove('solution-changed');
            this.hasChanges = false;
        }
        
        this.updateSaveButtonState();
        this.validateSolutionContent();
    }
    
    validateSolutionContent() {
        const content = this.solutionEditor.value.trim();
        
        // Basic validation rules
        const validations = {
            minLength: content.length >= 10,
            notEmpty: content.length > 0,
            hasAlphanumeric: /[a-zA-Z0-9]/.test(content)
        };
        
        // Visual feedback for validation
        if (!validations.notEmpty) {
            this.showValidationError('A solução não pode estar vazia');
        } else if (!validations.minLength) {
            this.showValidationWarning('Solução muito curta (mínimo 10 caracteres)');
        } else if (!validations.hasAlphanumeric) {
            this.showValidationError('A solução deve conter texto válido');
        } else {
            this.clearValidationMessages();
        }
        
        return Object.values(validations).every(v => v);
    }
    
    showValidationError(message) {
        this.solutionEditor.style.borderColor = '#ef4444';
        this.showFeedbackStatus(`⚠️ ${message}`, 'error', false);
    }
    
    showValidationWarning(message) {
        this.solutionEditor.style.borderColor = '#fbbf24';
        this.showFeedbackStatus(`⚠️ ${message}`, 'warning', false);
    }
    
    clearValidationMessages() {
        this.solutionEditor.style.borderColor = '';
        if (this.feedbackStatus.classList.contains('warning') || 
            this.feedbackStatus.classList.contains('error')) {
            this.hideFeedbackStatus();
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
    }
    
    selectClassification(type) {
        if (this.isLoading) return;
        
        this.selectedClassification = type;
        
        // Update button states with animation
        this.btnValid.classList.remove('selected');
        this.btnInvalid.classList.remove('selected');
        
        if (type === 'valid') {
            this.btnValid.classList.add('selected');
            this.animateButton(this.btnValid);
        } else if (type === 'invalid') {
            this.btnInvalid.classList.add('selected');
            this.animateButton(this.btnInvalid);
        }
        
        this.updateSaveButtonState();
        this.showFeedbackStatus(`Classificação selecionada: ${type === 'valid' ? 'Válida' : 'Inválida'}`, 'info', true);
    }
    
    animateButton(button) {
        button.style.transform = 'scale(0.95)';
        setTimeout(() => {
            button.style.transform = 'scale(1)';
        }, 150);
    }
    
    updateSaveButtonState() {
        // Enable save button if there's a classification or solution changes
        const canSave = (this.selectedClassification !== null || this.hasChanges) && !this.isLoading;
        this.btnSave.disabled = !canSave;
        
        // Update button text based on state
        if (this.isLoading) {
            this.btnSave.textContent = '⏳ Salvando...';
        } else if (this.hasChanges && this.selectedClassification) {
            this.btnSave.textContent = '💾 Salvar Classificação e Edição';
        } else if (this.hasChanges) {
            this.btnSave.textContent = '💾 Salvar Edição';
        } else if (this.selectedClassification) {
            this.btnSave.textContent = '💾 Salvar Classificação';
        } else {
            this.btnSave.textContent = '💾 Salvar Alterações';
        }
    }
    
    async saveFeedback() {
        if (this.isLoading) return;
        
        const id = this.analysisId.value;
        const editedSolution = this.solutionEditor.value.trim();
        
        // Validate inputs
        if (!id) {
            this.showFeedbackStatus('❌ Erro: ID da análise não encontrado', 'error');
            return;
        }
        
        if (this.selectedClassification === null && !this.hasChanges) {
            this.showFeedbackStatus('⚠️ Selecione uma classificação ou edite a solução', 'warning');
            return;
        }
        
        // Validate solution content if edited
        if (this.hasChanges && !this.validateSolutionContent()) {
            this.showFeedbackStatus('❌ Corrija os erros na solução antes de salvar', 'error');
            return;
        }
        
        // Prepare request data
        const requestData = {
            id: id,
            solucao_valida: this.selectedClassification === 'valid' ? true : 
                           this.selectedClassification === 'invalid' ? false : null,
            solucao_editada: this.hasChanges ? editedSolution : null
        };
        
        // Set loading state
        this.setLoadingState(true);
        this.showFeedbackStatus('💾 Salvando feedback...', 'loading');
        
        try {
            // Send AJAX request with timeout
            const response = await this.sendFeedbackRequest(requestData);
            
            if (response.ok) {
                const data = await response.json();
                await this.handleSaveSuccess(data);
            } else {
                const errorData = await response.json().catch(() => ({}));
                this.handleSaveError(errorData, response.status);
            }
        } catch (error) {
            this.handleNetworkError(error);
        } finally {
            this.setLoadingState(false);
        }
    }
    
    async sendFeedbackRequest(requestData) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
        
        try {
            const response = await fetch('/classificar_solucao', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData),
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            return response;
        } catch (error) {
            clearTimeout(timeoutId);
            throw error;
        }
    }
    
    async handleSaveSuccess(data) {
        // Success animation
        this.showFeedbackStatus('✅ Feedback salvo com sucesso!', 'success');
        
        // Update original solution to current value
        this.originalSolution = this.solutionEditor.value;
        this.hasChanges = false;
        this.solutionEditor.classList.remove('solution-changed');
        
        // Visual success feedback
        this.solutionEditor.style.borderColor = '#10b981';
        setTimeout(() => {
            this.solutionEditor.style.borderColor = '';
        }, 2000);
        
        // Update button states
        this.updateSaveButtonState();
        
        // Log success for analytics
        console.log('✅ Feedback saved successfully:', data);
    }
    
    handleSaveError(errorData, statusCode) {
        console.error('❌ Error saving feedback:', errorData);
        
        let errorMessage = 'Erro ao salvar feedback';
        
        // Handle different error types
        if (statusCode === 400) {
            errorMessage = errorData.error || 'Dados inválidos';
        } else if (statusCode === 404) {
            errorMessage = 'Análise não encontrada';
        } else if (statusCode === 500) {
            errorMessage = 'Erro interno do servidor';
        } else if (errorData && errorData.error) {
            errorMessage = errorData.error;
        }
        
        this.showFeedbackStatus(`❌ ${errorMessage}`, 'error');
        
        // Visual error feedback
        this.solutionEditor.style.borderColor = '#ef4444';
        setTimeout(() => {
            this.solutionEditor.style.borderColor = '';
        }, 3000);
    }
    
    handleNetworkError(error) {
        console.error('❌ Network error:', error);
        
        let errorMessage = 'Erro de conexão';
        
        if (error.name === 'AbortError') {
            errorMessage = 'Timeout - tente novamente';
        } else if (!navigator.onLine) {
            errorMessage = 'Sem conexão com a internet';
        }
        
        this.showFeedbackStatus(`❌ ${errorMessage}`, 'error');
    }
    
    setLoadingState(loading) {
        this.isLoading = loading;
        this.btnSave.disabled = loading;
        this.btnValid.disabled = loading;
        this.btnInvalid.disabled = loading;
        this.solutionEditor.disabled = loading;
        
        if (loading) {
            this.btnSave.style.opacity = '0.7';
        } else {
            this.btnSave.style.opacity = '1';
        }
        
        this.updateSaveButtonState();
    }
    
    showFeedbackStatus(message, type, autoHide = true) {
        this.feedbackStatus.className = `feedback-status ${type}`;
        this.feedbackStatus.textContent = message;
        this.feedbackStatus.style.display = 'block';
        
        // Auto-hide success and info messages
        if (autoHide && (type === 'success' || type === 'info')) {
            setTimeout(() => {
                this.hideFeedbackStatus();
            }, 3000);
        }
    }
    
    hideFeedbackStatus() {
        this.feedbackStatus.style.display = 'none';
    }
    
    handleKeyboardShortcuts(e) {
        // Ctrl/Cmd + S to save
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            if (!this.btnSave.disabled) {
                this.saveFeedback();
            }
        }
        
        // Ctrl/Cmd + 1 for valid classification
        if ((e.ctrlKey || e.metaKey) && e.key === '1') {
            e.preventDefault();
            this.selectClassification('valid');
        }
        
        // Ctrl/Cmd + 2 for invalid classification
        if ((e.ctrlKey || e.metaKey) && e.key === '2') {
            e.preventDefault();
            this.selectClassification('invalid');
        }
    }
    
    // Public methods for external access
    reset() {
        this.selectedClassification = null;
        this.hasChanges = false;
        this.solutionEditor.value = this.originalSolution;
        this.solutionEditor.classList.remove('solution-changed');
        this.btnValid.classList.remove('selected');
        this.btnInvalid.classList.remove('selected');
        this.updateSaveButtonState();
        this.hideFeedbackStatus();
    }
    
    getState() {
        return {
            selectedClassification: this.selectedClassification,
            hasChanges: this.hasChanges,
            isLoading: this.isLoading,
            currentSolution: this.solutionEditor ? this.solutionEditor.value : '',
            originalSolution: this.originalSolution
        };
    }
}

// Initialize feedback manager when script loads
let feedbackManager;
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        feedbackManager = new FeedbackManager();
    });
} else {
    feedbackManager = new FeedbackManager();
}

// Export for global access
window.FeedbackManager = FeedbackManager;
window.feedbackManager = feedbackManager;