/**
 * Dashboard JavaScript
 * Handles dynamic dashboard updates, filtering, and chart management
 * Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 8.1, 8.4
 */

class DashboardManager {
    constructor() {
        // Global variables
        this.currentPage = 1;
        this.currentFilters = {
            period_days: 30,
            criticality: ''
        };
        this.charts = {};
        this.refreshInterval = null;
        this.isLoading = false;
        this.isManualRefresh = false;
        this.lastDataLoad = 0;
        
        // Performance optimization flags
        this.enableAnimations = !this.isLowEndDevice();
        this.batchUpdates = true;
        
        this.init();
    }
    
    init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initializeDashboard());
        } else {
            this.initializeDashboard();
        }
    }
    
    initializeDashboard() {
        console.log('🚀 Initializing dashboard...');
        
        // Bind event listeners
        this.bindEvents();
        
        // Load initial dashboard data
        this.loadDashboard();
        
        // Set up auto-refresh (every 5 minutes)
        this.setupAutoRefresh();
        
        console.log('✅ Dashboard initialized');
    }
    
    bindEvents() {
        // Filter change handlers
        const periodFilter = document.getElementById('periodFilter');
        const criticalityFilter = document.getElementById('criticalityFilter');
        
        if (periodFilter) {
            periodFilter.addEventListener('change', () => this.onFilterChange());
        }
        
        if (criticalityFilter) {
            criticalityFilter.addEventListener('change', () => this.onFilterChange());
        }
        
        // Manual refresh button
        const refreshBtn = document.querySelector('.btn-filter');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.applyFilters());
        }
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboardShortcuts(e));
        
        // Visibility change handler for auto-refresh
        document.addEventListener('visibilitychange', () => this.handleVisibilityChange());
        
        // Window resize handler for chart responsiveness
        window.addEventListener('resize', () => this.handleWindowResize());
    }
    
    onFilterChange() {
        // Debounce filter changes
        clearTimeout(this.filterTimeout);
        this.filterTimeout = setTimeout(() => {
            this.applyFilters();
        }, 500);
    }
    
    applyFilters() {
        if (this.isLoading) return;
        
        const periodFilter = document.getElementById('periodFilter');
        const criticalityFilter = document.getElementById('criticalityFilter');
        
        if (!periodFilter || !criticalityFilter) return;
        
        this.currentFilters = {
            period_days: parseInt(periodFilter.value),
            criticality: criticalityFilter.value
        };
        
        this.currentPage = 1; // Reset to first page when filters change
        this.isManualRefresh = true; // Mark as manual refresh for cache bypass
        this.loadDashboard();
        
        // Update URL with current filters (for bookmarking)
        this.updateURL();
    }
    
    updateURL() {
        const params = new URLSearchParams();
        params.set('period_days', this.currentFilters.period_days);
        if (this.currentFilters.criticality) {
            params.set('criticality', this.currentFilters.criticality);
        }
        
        const newURL = `${window.location.pathname}?${params.toString()}`;
        window.history.replaceState({}, '', newURL);
    }
    
    async loadDashboard() {
        if (this.isLoading) return;
        
        this.setLoadingState(true);
        
        try {
            // Load metrics and history in parallel
            await Promise.all([
                this.loadMetrics(),
                this.loadHistory()
            ]);
            
            this.showSuccessIndicator();
        } catch (error) {
            console.error('❌ Error loading dashboard:', error);
            this.showError('Erro ao carregar dados do dashboard');
        } finally {
            this.setLoadingState(false);
        }
    }
    
    async loadMetrics() {
        try {
            const params = new URLSearchParams();
            params.append('period_days', this.currentFilters.period_days);
            if (this.currentFilters.criticality) {
                params.append('criticality', this.currentFilters.criticality);
            }
            
            const response = await this.fetchWithTimeout(`/api/metrics?${params}`, 15000);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            if (result.status !== 'success') {
                throw new Error(result.error || 'Erro desconhecido');
            }
            
            // Convert accuracy rate from decimal to percentage if needed
            if (result.data.ai_accuracy_rate !== undefined && result.data.ai_accuracy_rate <= 1) {
                result.data.ai_accuracy_rate = result.data.ai_accuracy_rate * 100;
            }
            
            this.displayMetrics(result.data);
            this.displayCharts(result.data);
            this.lastDataLoad = Date.now();
            
        } catch (error) {
            console.error('❌ Error loading metrics:', error);
            this.showMetricsError(error.message);
        } finally {
            this.isManualRefresh = false; // Reset manual refresh flag
        }
    }
    
    async loadHistory(page = 1) {
        try {
            const params = new URLSearchParams();
            params.append('page', page);
            params.append('limit', '10');
            params.append('period_days', this.currentFilters.period_days);
            if (this.currentFilters.criticality) {
                params.append('criticality', this.currentFilters.criticality);
            }
            
            const response = await this.fetchWithTimeout(`/api/analysis-history?${params}`, 15000);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            if (result.status !== 'success') {
                throw new Error(result.error || 'Erro desconhecido');
            }
            
            this.displayHistory(result.data);
            this.currentPage = page;
            
        } catch (error) {
            console.error('❌ Error loading history:', error);
            this.showHistoryError(error.message);
        }
    }
    
    async fetchWithTimeout(url, timeout = 10000) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);
        
        try {
            // Add cache-busting parameter for fresh data when needed
            const separator = url.includes('?') ? '&' : '?';
            const cacheBuster = this.shouldBypassCache() ? `${separator}_t=${Date.now()}` : '';
            
            const response = await fetch(url + cacheBuster, {
                signal: controller.signal,
                headers: {
                    'Accept': 'application/json',
                    'Cache-Control': this.getCacheControl(),
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            clearTimeout(timeoutId);
            return response;
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                throw new Error('Timeout - requisição demorou muito para responder');
            }
            throw error;
        }
    }
    
    shouldBypassCache() {
        // Bypass cache for manual refreshes or when data is stale
        return this.isManualRefresh || (Date.now() - this.lastDataLoad > 300000); // 5 minutes
    }
    
    getCacheControl() {
        // Use different cache strategies based on data freshness needs
        if (this.shouldBypassCache()) {
            return 'no-cache, no-store, must-revalidate';
        }
        return 'max-age=300'; // 5 minutes cache for normal requests
    }
    
    displayMetrics(data) {
        const errorCounts = data.error_count_by_criticality || {};
        const totalErrors = data.total_errors || 0;
        const accuracyRate = data.ai_accuracy_rate || 0;
        const avgResolutionTime = data.average_resolution_time || 0;
        
        const metricsHtml = `
            <div class="metrics-grid">
                <div class="metric-card" data-metric="total">
                    <h3>📊 Total de Erros</h3>
                    <div class="metric-value info">${this.formatNumber(totalErrors)}</div>
                    <div class="metric-subtitle">Últimos ${this.currentFilters.period_days} dias</div>
                </div>
                <div class="metric-card" data-metric="alta">
                    <h3>🔴 Criticidade Alta</h3>
                    <div class="metric-value error">${this.formatNumber(errorCounts.alta || 0)}</div>
                    <div class="metric-subtitle">Erros críticos</div>
                </div>
                <div class="metric-card" data-metric="media">
                    <h3>🟡 Criticidade Média</h3>
                    <div class="metric-value warning">${this.formatNumber(errorCounts.media || 0)}</div>
                    <div class="metric-subtitle">Erros moderados</div>
                </div>
                <div class="metric-card" data-metric="baixa">
                    <h3>🟢 Criticidade Baixa</h3>
                    <div class="metric-value success">${this.formatNumber(errorCounts.baixa || 0)}</div>
                    <div class="metric-subtitle">Erros menores</div>
                </div>
                <div class="metric-card" data-metric="accuracy">
                    <h3>🎯 Taxa de Acerto da IA</h3>
                    <div class="metric-value ${this.getAccuracyClass(accuracyRate)}">${accuracyRate.toFixed(1)}%</div>
                    <div class="metric-subtitle">Soluções válidas</div>
                </div>
                <div class="metric-card" data-metric="time">
                    <h3>⏱️ Tempo Médio</h3>
                    <div class="metric-value info">${this.formatTime(avgResolutionTime)}</div>
                    <div class="metric-subtitle">Resolução de problemas</div>
                </div>
            </div>
        `;
        
        const metricsSection = document.getElementById('metricsSection');
        if (metricsSection) {
            metricsSection.innerHTML = metricsHtml;
            this.animateMetricCards();
        }
    }
    
    displayCharts(data) {
        const errorCounts = data.error_count_by_criticality || {};
        const accuracyRate = data.ai_accuracy_rate || 0;
        
        // Show charts section
        const chartsSection = document.getElementById('chartsSection');
        if (chartsSection) {
            chartsSection.style.display = 'block';
        }
        
        // Destroy existing charts
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        this.charts = {};
        
        // Create charts with error handling
        try {
            this.createCriticalityChart(errorCounts);
            this.createAccuracyChart(accuracyRate);
        } catch (error) {
            console.error('❌ Error creating charts:', error);
        }
    }
    
    createCriticalityChart(errorCounts) {
        const criticalityCtx = document.getElementById('criticalityChart');
        if (!criticalityCtx) return;
        
        const ctx = criticalityCtx.getContext('2d');
        
        this.charts.criticality = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Alta', 'Média', 'Baixa'],
                datasets: [{
                    data: [
                        errorCounts.alta || 0,
                        errorCounts.media || 0,
                        errorCounts.baixa || 0
                    ],
                    backgroundColor: [
                        '#ef4444',
                        '#fbbf24',
                        '#10b981'
                    ],
                    borderColor: [
                        '#dc2626',
                        '#f59e0b',
                        '#059669'
                    ],
                    borderWidth: 2,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: '#f1f5f9',
                            font: {
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                },
                animation: {
                    animateRotate: true,
                    duration: 1000
                }
            }
        });
    }
    
    createAccuracyChart(accuracyRate) {
        const accuracyCtx = document.getElementById('accuracyChart');
        if (!accuracyCtx) return;
        
        const ctx = accuracyCtx.getContext('2d');
        
        this.charts.accuracy = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Válidas', 'Inválidas'],
                datasets: [{
                    data: [accuracyRate, 100 - accuracyRate],
                    backgroundColor: [
                        '#10b981',
                        '#ef4444'
                    ],
                    borderColor: [
                        '#059669',
                        '#dc2626'
                    ],
                    borderWidth: 2,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: '#f1f5f9',
                            font: {
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                return `${label}: ${value.toFixed(1)}%`;
                            }
                        }
                    }
                },
                animation: {
                    animateRotate: true,
                    duration: 1000
                }
            }
        });
    }
    
    displayHistory(data) {
        const analyses = data.analyses || [];
        const pagination = data.pagination || {};
        
        const historyContent = document.getElementById('historyContent');
        if (!historyContent) return;
        
        if (analyses.length === 0) {
            historyContent.innerHTML = 
                '<div class="loading">📭 Nenhuma análise encontrada para os filtros selecionados</div>';
            return;
        }
        
        let historyHtml = `
            <div class="table-container">
                <table class="history-table">
                    <thead>
                        <tr>
                            <th>Data</th>
                            <th>Erro</th>
                            <th>Criticidade</th>
                            <th>Origem</th>
                            <th>Solução Válida</th>
                            <th>Editada</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        analyses.forEach((analysis, index) => {
            const date = analysis.data_incidente ? 
                this.formatDate(analysis.data_incidente) : 
                'N/A';
            
            const validationClass = analysis.solucao_valida === 'true' ? 'validation-true' :
                                  analysis.solucao_valida === 'false' ? 'validation-false' :
                                  'validation-null';
            
            const validationText = analysis.solucao_valida === 'true' ? 'Válida' :
                                 analysis.solucao_valida === 'false' ? 'Inválida' :
                                 'Não avaliada';
            
            historyHtml += `
                <tr data-index="${index}" class="history-row">
                    <td class="date-cell">${date}</td>
                    <td class="error-cell">
                        <div class="truncate" title="${this.escapeHtml(analysis.erro || 'N/A')}">
                            ${this.escapeHtml(analysis.erro || 'N/A')}
                        </div>
                    </td>
                    <td class="criticality-cell">
                        <span class="criticality-badge criticality-${analysis.criticidade || 'baixa'}">
                            ${this.capitalizeCriticality(analysis.criticidade || 'N/A')}
                        </span>
                    </td>
                    <td class="origin-cell">${this.escapeHtml(analysis.origem || 'N/A')}</td>
                    <td class="validation-cell">
                        <span class="validation-badge ${validationClass}">${validationText}</span>
                    </td>
                    <td class="edited-cell">
                        ${analysis.solucao_editada ? '✅' : '❌'}
                    </td>
                </tr>
            `;
        });
        
        historyHtml += `
                    </tbody>
                </table>
            </div>
            <div class="pagination">
                <button class="pagination-btn" onclick="dashboardManager.loadHistory(${pagination.prev_page})" ${!pagination.has_prev ? 'disabled' : ''}>
                    ⬅️ Anterior
                </button>
                <span class="current-page">Página ${pagination.current_page} de ${pagination.total_pages}</span>
                <button class="pagination-btn" onclick="dashboardManager.loadHistory(${pagination.next_page})" ${!pagination.has_next ? 'disabled' : ''}>
                    Próxima ➡️
                </button>
            </div>
            <div class="pagination-info">
                Total: ${this.formatNumber(pagination.total_count)} análises
            </div>
        `;
        
        historyContent.innerHTML = historyHtml;
        this.animateHistoryRows();
    }
    
    // Performance detection
    isLowEndDevice() {
        // Detect low-end devices to disable animations
        const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
        const slowConnection = connection && (connection.effectiveType === 'slow-2g' || connection.effectiveType === '2g');
        const lowMemory = navigator.deviceMemory && navigator.deviceMemory < 4;
        const oldBrowser = !window.IntersectionObserver || !window.requestIdleCallback;
        
        return slowConnection || lowMemory || oldBrowser;
    }
    
    // Utility methods
    formatNumber(num) {
        return new Intl.NumberFormat('pt-BR').format(num);
    }
    
    formatTime(hours) {
        if (hours < 1) {
            return `${Math.round(hours * 60)}min`;
        } else if (hours < 24) {
            return `${hours.toFixed(1)}h`;
        } else {
            const days = Math.floor(hours / 24);
            const remainingHours = Math.round(hours % 24);
            return `${days}d ${remainingHours}h`;
        }
    }
    
    formatDate(dateString) {
        try {
            const date = new Date(dateString);
            return date.toLocaleString('pt-BR', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch (error) {
            return 'Data inválida';
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    capitalizeCriticality(criticality) {
        const map = {
            'baixa': 'Baixa',
            'media': 'Média',
            'alta': 'Alta'
        };
        return map[criticality] || criticality;
    }
    
    getAccuracyClass(rate) {
        if (rate >= 80) return 'success';
        if (rate >= 60) return 'warning';
        return 'error';
    }
    
    // Animation methods
    animateMetricCards() {
        const cards = document.querySelectorAll('.metric-card');
        cards.forEach((card, index) => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            
            setTimeout(() => {
                card.style.transition = 'all 0.5s ease';
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, index * 100);
        });
    }
    
    animateHistoryRows() {
        const rows = document.querySelectorAll('.history-row');
        rows.forEach((row, index) => {
            row.style.opacity = '0';
            row.style.transform = 'translateX(-20px)';
            
            setTimeout(() => {
                row.style.transition = 'all 0.3s ease';
                row.style.opacity = '1';
                row.style.transform = 'translateX(0)';
            }, index * 50);
        });
    }
    
    // State management
    setLoadingState(loading) {
        this.isLoading = loading;
        
        const refreshBtn = document.querySelector('.btn-filter');
        if (refreshBtn) {
            refreshBtn.disabled = loading;
            refreshBtn.textContent = loading ? '⏳ Carregando...' : '🔄 Atualizar';
        }
        
        // Show/hide loading indicators
        if (loading) {
            this.showLoadingIndicators();
        }
    }
    
    showLoadingIndicators() {
        const metricsSection = document.getElementById('metricsSection');
        const historyContent = document.getElementById('historyContent');
        
        if (metricsSection) {
            metricsSection.innerHTML = '<div class="loading">⏳ Carregando métricas...</div>';
        }
        
        if (historyContent) {
            historyContent.innerHTML = '<div class="loading">⏳ Carregando histórico...</div>';
        }
    }
    
    showSuccessIndicator() {
        // Brief success indicator
        const refreshBtn = document.querySelector('.btn-filter');
        if (refreshBtn) {
            const originalText = refreshBtn.textContent;
            refreshBtn.textContent = '✅ Atualizado';
            refreshBtn.style.backgroundColor = '#10b981';
            
            setTimeout(() => {
                refreshBtn.textContent = originalText;
                refreshBtn.style.backgroundColor = '';
            }, 1500);
        }
    }
    
    // Error handling
    showError(message) {
        const errorHtml = `<div class="error-message">❌ ${message}</div>`;
        
        const metricsSection = document.getElementById('metricsSection');
        const historyContent = document.getElementById('historyContent');
        
        if (metricsSection) {
            metricsSection.innerHTML = errorHtml;
        }
        
        if (historyContent) {
            historyContent.innerHTML = errorHtml;
        }
    }
    
    showMetricsError(message) {
        const metricsSection = document.getElementById('metricsSection');
        if (metricsSection) {
            metricsSection.innerHTML = 
                `<div class="error-message">❌ Erro ao carregar métricas: ${message}</div>`;
        }
    }
    
    showHistoryError(message) {
        const historyContent = document.getElementById('historyContent');
        if (historyContent) {
            historyContent.innerHTML = 
                `<div class="error-message">❌ Erro ao carregar histórico: ${message}</div>`;
        }
    }
    
    // Auto-refresh functionality
    setupAutoRefresh() {
        // Refresh every 5 minutes when page is visible
        this.refreshInterval = setInterval(() => {
            if (!document.hidden && !this.isLoading) {
                console.log('🔄 Auto-refreshing dashboard...');
                this.loadDashboard();
            }
        }, 5 * 60 * 1000); // 5 minutes
    }
    
    handleVisibilityChange() {
        if (!document.hidden && !this.isLoading) {
            // Page became visible, refresh data
            this.loadDashboard();
        }
    }
    
    handleWindowResize() {
        // Debounce resize events
        clearTimeout(this.resizeTimeout);
        this.resizeTimeout = setTimeout(() => {
            // Resize charts
            Object.values(this.charts).forEach(chart => {
                if (chart && typeof chart.resize === 'function') {
                    chart.resize();
                }
            });
        }, 250);
    }
    
    handleKeyboardShortcuts(e) {
        // F5 or Ctrl+R to refresh
        if (e.key === 'F5' || (e.ctrlKey && e.key === 'r')) {
            e.preventDefault();
            this.loadDashboard();
        }
        
        // Ctrl+1-4 for quick filter changes
        if (e.ctrlKey && ['1', '2', '3', '4'].includes(e.key)) {
            e.preventDefault();
            const periodFilter = document.getElementById('periodFilter');
            if (periodFilter) {
                const periods = ['7', '30', '90', '365'];
                const index = parseInt(e.key) - 1;
                if (periods[index]) {
                    periodFilter.value = periods[index];
                    this.applyFilters();
                }
            }
        }
    }
    
    // Cleanup
    destroy() {
        // Clear intervals
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        // Destroy charts
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        
        // Remove event listeners
        document.removeEventListener('visibilitychange', this.handleVisibilityChange);
        window.removeEventListener('resize', this.handleWindowResize);
        
        console.log('🧹 Dashboard manager destroyed');
    }
}

// Initialize dashboard manager
let dashboardManager;
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        dashboardManager = new DashboardManager();
    });
} else {
    dashboardManager = new DashboardManager();
}

// Export for global access
window.DashboardManager = DashboardManager;
window.dashboardManager = dashboardManager;

// Legacy function for backward compatibility
function applyFilters() {
    if (window.dashboardManager) {
        window.dashboardManager.applyFilters();
    }
}

function loadHistory(page) {
    if (window.dashboardManager) {
        window.dashboardManager.loadHistory(page);
    }
}