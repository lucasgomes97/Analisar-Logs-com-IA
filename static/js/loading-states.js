/**
 * Loading States JavaScript
 * Handles loading indicators, progress bars, and user feedback
 * Requirements: 8.2, 8.3 - Loading states and feedback visual
 */

class LoadingManager {
    constructor() {
        this.activeLoaders = new Map();
        this.defaultOptions = {
            showProgress: true,
            showMessage: true,
            timeout: 30000, // 30 seconds
            overlay: false,
            position: 'inline'
        };
        
        this.init();
    }
    
    init() {
        // Create global loading overlay
        this.createGlobalOverlay();
        
        // Enhance existing loading functionality
        this.enhanceExistingLoaders();
        
        console.log('✅ Loading manager initialized');
    }
    
    createGlobalOverlay() {
        const overlay = document.createElement('div');
        overlay.id = 'globalLoadingOverlay';
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div class="loading-spinner">
                <div class="spinner-ring"></div>
                <div class="loading-text">Carregando...</div>
            </div>
        `;
        overlay.style.display = 'none';
        document.body.appendChild(overlay);
    }
    
    enhanceExistingLoaders() {
        // Enhance the existing log analysis loading
        const existingProgressBar = document.getElementById('loading-bar');
        if (existingProgressBar) {
            this.enhanceProgressBar(existingProgressBar);
        }
    }
    
    enhanceProgressBar(progressBar) {
        // Add cancel button to existing progress bar
        const cancelBtn = document.createElement('button');
        cancelBtn.className = 'cancel-loading-btn';
        cancelBtn.textContent = '❌ Cancelar';
        cancelBtn.style.marginTop = '10px';
        cancelBtn.style.display = 'none';
        
        cancelBtn.addEventListener('click', () => {
            this.cancelLoading('logAnalysis');
        });
        
        progressBar.parentNode.appendChild(cancelBtn);
        
        // Show cancel button after 10 seconds
        setTimeout(() => {
            if (progressBar.style.display !== 'none') {
                cancelBtn.style.display = 'inline-block';
            }
        }, 10000);
    }
    
    showLoading(id, options = {}) {
        const config = { ...this.defaultOptions, ...options };
        
        // Create loading element
        const loader = this.createLoader(id, config);
        
        // Store loader reference
        this.activeLoaders.set(id, {
            element: loader,
            config: config,
            startTime: Date.now(),
            timeout: null
        });
        
        // Set timeout if specified
        if (config.timeout > 0) {
            const timeoutId = setTimeout(() => {
                this.hideLoading(id);
                this.showTimeoutMessage(id);
            }, config.timeout);
            
            this.activeLoaders.get(id).timeout = timeoutId;
        }
        
        // Show the loader
        this.displayLoader(loader, config);
        
        return loader;
    }
    
    createLoader(id, config) {
        const loader = document.createElement('div');
        loader.id = `loader-${id}`;
        loader.className = 'custom-loader';
        
        let content = '';
        
        if (config.showProgress) {
            content += `
                <div class="progress-container">
                    <div class="progress-bar">
                        <div class="progress-fill" id="progress-fill-${id}"></div>
                    </div>
                    <div class="progress-text" id="progress-text-${id}">0%</div>
                </div>
            `;
        }
        
        if (config.showMessage) {
            content += `
                <div class="loading-message" id="loading-message-${id}">
                    ${config.message || 'Carregando...'}
                </div>
            `;
        }
        
        content += `
            <div class="loading-spinner">
                <div class="spinner-dots">
                    <div class="dot"></div>
                    <div class="dot"></div>
                    <div class="dot"></div>
                </div>
            </div>
        `;
        
        if (config.showCancel) {
            content += `
                <button class="cancel-btn" onclick="loadingManager.cancelLoading('${id}')">
                    ❌ Cancelar
                </button>
            `;
        }
        
        loader.innerHTML = content;
        
        return loader;
    }
    
    displayLoader(loader, config) {
        if (config.overlay) {
            this.showGlobalOverlay(loader);
        } else {
            // Find target container or use default
            const container = config.container ? 
                document.querySelector(config.container) : 
                document.body;
            
            container.appendChild(loader);
        }
        
        // Animate in
        loader.style.opacity = '0';
        loader.style.transform = 'translateY(10px)';
        
        setTimeout(() => {
            loader.style.transition = 'all 0.3s ease';
            loader.style.opacity = '1';
            loader.style.transform = 'translateY(0)';
        }, 10);
    }
    
    updateProgress(id, percentage, message = null) {
        const loader = this.activeLoaders.get(id);
        if (!loader) return;
        
        const progressFill = document.getElementById(`progress-fill-${id}`);
        const progressText = document.getElementById(`progress-text-${id}`);
        const messageElement = document.getElementById(`loading-message-${id}`);
        
        if (progressFill) {
            progressFill.style.width = `${Math.min(100, Math.max(0, percentage))}%`;
        }
        
        if (progressText) {
            progressText.textContent = `${Math.round(percentage)}%`;
        }
        
        if (message && messageElement) {
            messageElement.textContent = message;
        }
        
        // Add completion animation at 100%
        if (percentage >= 100) {
            setTimeout(() => {
                this.hideLoading(id);
            }, 500);
        }
    }
    
    updateMessage(id, message) {
        const messageElement = document.getElementById(`loading-message-${id}`);
        if (messageElement) {
            messageElement.textContent = message;
        }
    }
    
    hideLoading(id) {
        const loader = this.activeLoaders.get(id);
        if (!loader) return;
        
        // Clear timeout
        if (loader.timeout) {
            clearTimeout(loader.timeout);
        }
        
        // Animate out
        loader.element.style.transition = 'all 0.3s ease';
        loader.element.style.opacity = '0';
        loader.element.style.transform = 'translateY(-10px)';
        
        setTimeout(() => {
            if (loader.element.parentNode) {
                loader.element.parentNode.removeChild(loader.element);
            }
        }, 300);
        
        // Remove from active loaders
        this.activeLoaders.delete(id);
        
        // Hide global overlay if no more loaders
        if (this.activeLoaders.size === 0) {
            this.hideGlobalOverlay();
        }
    }
    
    cancelLoading(id) {
        const loader = this.activeLoaders.get(id);
        if (!loader) return;
        
        // Trigger cancel event
        const cancelEvent = new CustomEvent('loadingCancelled', {
            detail: { id: id, duration: Date.now() - loader.startTime }
        });
        document.dispatchEvent(cancelEvent);
        
        // Hide loader
        this.hideLoading(id);
        
        // Show cancellation message
        this.showMessage('Operação cancelada', 'warning');
    }
    
    showGlobalOverlay(content = null) {
        const overlay = document.getElementById('globalLoadingOverlay');
        if (overlay) {
            if (content) {
                overlay.querySelector('.loading-spinner').replaceWith(content);
            }
            overlay.style.display = 'flex';
        }
    }
    
    hideGlobalOverlay() {
        const overlay = document.getElementById('globalLoadingOverlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }
    
    showTimeoutMessage(id) {
        this.showMessage(
            `Operação "${id}" demorou muito para responder e foi cancelada`,
            'error'
        );
    }
    
    showMessage(message, type = 'info', duration = 5000) {
        const messageElement = document.createElement('div');
        messageElement.className = `toast-message toast-${type}`;
        
        const icon = {
            'success': '✅',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️'
        }[type] || 'ℹ️';
        
        messageElement.innerHTML = `
            <div class="toast-content">
                <span class="toast-icon">${icon}</span>
                <span class="toast-text">${message}</span>
                <button class="toast-close" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
        `;
        
        // Position toast
        messageElement.style.position = 'fixed';
        messageElement.style.top = '20px';
        messageElement.style.right = '20px';
        messageElement.style.zIndex = '10000';
        
        document.body.appendChild(messageElement);
        
        // Auto-remove after duration
        if (duration > 0) {
            setTimeout(() => {
                if (messageElement.parentNode) {
                    messageElement.remove();
                }
            }, duration);
        }
        
        return messageElement;
    }
    
    // Enhanced loading for specific operations
    showAnalysisLoading() {
        return this.showLoading('analysis', {
            message: 'Analisando log com IA...',
            showProgress: true,
            showCancel: true,
            timeout: 180000, // 3 minutes
            container: '#logForm'
        });
    }
    
    showFeedbackLoading() {
        return this.showLoading('feedback', {
            message: 'Salvando feedback...',
            showProgress: false,
            timeout: 30000,
            overlay: false
        });
    }
    
    showDashboardLoading() {
        return this.showLoading('dashboard', {
            message: 'Carregando métricas...',
            showProgress: false,
            timeout: 15000,
            container: '#metricsSection'
        });
    }
    
    // Button loading states
    setButtonLoading(button, loading = true, originalText = null) {
        if (loading) {
            if (!button.dataset.originalText) {
                button.dataset.originalText = button.textContent;
            }
            button.textContent = '⏳ Carregando...';
            button.disabled = true;
            button.classList.add('loading');
        } else {
            button.textContent = originalText || button.dataset.originalText || button.textContent;
            button.disabled = false;
            button.classList.remove('loading');
            delete button.dataset.originalText;
        }
    }
    
    // Form loading states
    setFormLoading(form, loading = true) {
        const inputs = form.querySelectorAll('input, textarea, select, button');
        
        inputs.forEach(input => {
            if (loading) {
                input.disabled = true;
                input.classList.add('loading-disabled');
            } else {
                input.disabled = false;
                input.classList.remove('loading-disabled');
            }
        });
        
        if (loading) {
            form.classList.add('form-loading');
        } else {
            form.classList.remove('form-loading');
        }
    }
    
    // Progress tracking for multiple operations
    createProgressTracker(id, operations) {
        const tracker = {
            id: id,
            operations: operations,
            completed: 0,
            total: operations.length,
            progress: 0
        };
        
        this.showLoading(id, {
            message: `Executando ${tracker.total} operações...`,
            showProgress: true
        });
        
        return {
            complete: (operationName) => {
                tracker.completed++;
                tracker.progress = (tracker.completed / tracker.total) * 100;
                
                this.updateProgress(
                    id, 
                    tracker.progress, 
                    `Concluído: ${operationName} (${tracker.completed}/${tracker.total})`
                );
                
                if (tracker.completed >= tracker.total) {
                    setTimeout(() => this.hideLoading(id), 1000);
                }
            },
            
            error: (operationName, error) => {
                console.error(`Error in operation "${operationName}":`, error);
                this.hideLoading(id);
                this.showMessage(
                    `Erro em "${operationName}": ${error}`,
                    'error'
                );
            }
        };
    }
    
    // Utility methods
    isLoading(id) {
        return this.activeLoaders.has(id);
    }
    
    getActiveLoaders() {
        return Array.from(this.activeLoaders.keys());
    }
    
    hideAllLoading() {
        const loaderIds = Array.from(this.activeLoaders.keys());
        loaderIds.forEach(id => this.hideLoading(id));
    }
    
    // Performance monitoring
    getLoadingDuration(id) {
        const loader = this.activeLoaders.get(id);
        return loader ? Date.now() - loader.startTime : 0;
    }
    
    // Request cancellation with AbortController
    async fetchWithTimeout(url, options = {}, timeout = 30000) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);
        
        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            return response;
        } catch (error) {
            clearTimeout(timeoutId);
            console.error('Fetch error:', error);
            if (error.name === 'AbortError') {
                throw new Error('Request timeout');
            }
            throw error;
        }
    }
    
    // Accessibility improvements
    announceToScreenReader(message) {
        const announcement = document.createElement('div');
        announcement.setAttribute('aria-live', 'polite');
        announcement.setAttribute('aria-atomic', 'true');
        announcement.style.position = 'absolute';
        announcement.style.left = '-10000px';
        announcement.style.width = '1px';
        announcement.style.height = '1px';
        announcement.style.overflow = 'hidden';
        
        document.body.appendChild(announcement);
        announcement.textContent = message;
        
        setTimeout(() => {
            document.body.removeChild(announcement);
        }, 1000);
    }
}

// Initialize loading manager
let loadingManager;
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        loadingManager = new LoadingManager();
    });
} else {
    loadingManager = new LoadingManager();
}

// Export for global access
window.LoadingManager = LoadingManager;
window.loadingManager = loadingManager;