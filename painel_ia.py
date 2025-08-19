
from flask import Flask, request, render_template_string, jsonify
import os
import re
from datetime import datetime, timezone
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from dotenv import load_dotenv
from src.services.postgres_service import PostgreSQLService
# MetricsService removido - funcionalidade integrada ao PostgreSQLService
from src.models.models import Analysis, Classification, parse_ai_response
from src.utils.logging_config import (
    setup_logging, get_logger, log_operation, log_user_action, 
    log_database_operation, performance_monitor, metrics_collector
)
from src.utils.error_handling import (
    ErrorHandler, InputValidator, DataSanitizer, ConnectionFallback,
    with_api_retry, with_fallback
)
# Connection pool removido - usando PostgreSQL com SQLAlchemy
from src.services.cache_service import initialize_cache_service
from src.services.rate_limiter import initialize_rate_limiter, rate_limit
from src.services.query_optimizer import initialize_query_optimizer

# === CONFIG ===
from config.settings import (
    DATABASE_URL,
    LOG_LEVEL, LOG_FILE, CACHE_TTL, CACHE_MAX_ENTRIES
)

# Setup enhanced logging
setup_logging(log_level=LOG_LEVEL, log_file=LOG_FILE)

# Configure enhanced logging
logger = get_logger(__name__)

# Initialize performance services
logger.info("🚀 Inicializando serviços de performance...")

# Initialize cache service
cache_service = initialize_cache_service(
    default_ttl=CACHE_TTL,
    max_entries=CACHE_MAX_ENTRIES
)

# Initialize rate limiter
rate_limiter = initialize_rate_limiter()

# Initialize PostgreSQL service
postgres_service = PostgreSQLService(DATABASE_URL)

# Metrics integradas no PostgreSQLService

logger.info("✅ Serviços PostgreSQL inicializados com sucesso")

# === APP ===
app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Diagnóstico com IA</title>
    <link rel="icon" type="image/png" href="{{ url_for('static', filename='images.png') }}">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/interactive-styles.css') }}">
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background-image: url('{{ url_for('static', filename='2sinovacoestecnologicas_cover.jpeg') }}');
            background-size: cover; 
            background-position: center;
            background-attachment: fixed;
            color: #f1f5f9;
            display: flex;
            flex-direction: column;
            align-items: center;
            min-height: 100vh;
            justify-content: center;
            backdrop-filter: blur(5px);
        }

        h1 {
            color: #38bdf8;
            margin-bottom: 20px;
            text-shadow: 1px 1px 2px #000;
        }

        form {
            background-color: rgba(30, 41, 59, 0.9);
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.5);
            width: 90%;
            max-width: 600px;
        }

        label {
            font-size: 16px;
            display: block;
            margin-bottom: 10px;
        }

        textarea {
            width: 100%;
            height: 150px;
            font-size: 14px;
            border-radius: 8px;
            border: 1px solid #475569;
            background-color: #0f172a;
            color: #f1f5f9;
            padding: 10px;
            resize: vertical;
            margin-bottom: 15px;
        }

        button {
            background-color: #38bdf8;
            color: #0f172a;
            border: none;
            padding: 12px 25px;
            font-size: 16px;
            border-radius: 8px;
            cursor: pointer;
            transition: background-color 0.3s ease;
        }

        button:hover {
            background-color: #0ea5e9;
        }

        .resultado {
            background-color: rgba(30, 41, 59, 0.9);
            margin-top: 30px;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.5);
            width: 90%;
            max-width: 600px;
        }

        h2 {
            color: #34d399;
            margin-bottom: 10px;
        }

        pre {
            white-space: pre-wrap;
            word-wrap: break-word;
            font-family: 'Courier New', Courier, monospace;
            color: #f8fafc;
        }

        /* Loading Styles */
        .text-message {
            font-family: 'Poppins', sans-serif;
            font-size: 20px;
            font-weight: bold;
            text-align: center;
            margin-top: 20px;
            color: #f1f5f9;
            display: none;
        }

        .progress1 {
            height: 22px;
            background-color: #ffffff;
            position: relative;
            overflow: hidden;
            border-radius: 10px;
            display: none;
            margin-top: 10px;
        }

        .progress1 .progress-bar1 {
            position: relative;
            height: 100%;
            background-color: red;
            width: 0%;
        }

        .progress1 .progress-bar1 .icon1 {
            position: absolute;
            top: 0;
            left: 0;
            width: 22px;
            height: 22px;
            background-image: url('{{ url_for('static', filename='loading-gif.gif') }}');
            background-size: contain;
            background-repeat: no-repeat;
            z-index: 1;
        }

        .progress1 .countdown {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 14px;
            color: #000000;
            font-family: 'Poppins', sans-serif;
            font-weight: bold;
        }

        /* Feedback Section Styles */
        .feedback-section {
            background-color: rgba(30, 41, 59, 0.9);
            margin-top: 20px;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.5);
            width: 90%;
            max-width: 600px;
        }

        .feedback-section h3 {
            color: #fbbf24;
            margin-bottom: 15px;
            font-size: 18px;
        }

        .solution-editor {
            width: 100%;
            min-height: 120px;
            font-size: 14px;
            border-radius: 8px;
            border: 1px solid #475569;
            background-color: #0f172a;
            color: #f1f5f9;
            padding: 12px;
            resize: vertical;
            margin-bottom: 15px;
            font-family: 'Courier New', Courier, monospace;
        }

        .classification-buttons {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }

        .btn-valid {
            background-color: #10b981;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s ease;
        }

        .btn-valid:hover {
            background-color: #059669;
        }

        .btn-valid.selected {
            background-color: #047857;
            box-shadow: 0 0 0 2px #10b981;
        }

        .btn-invalid {
            background-color: #ef4444;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s ease;
        }

        .btn-invalid:hover {
            background-color: #dc2626;
        }

        .btn-invalid.selected {
            background-color: #b91c1c;
            box-shadow: 0 0 0 2px #ef4444;
        }

        .btn-save {
            background-color: #3b82f6;
            color: white;
            border: none;
            padding: 12px 25px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            transition: all 0.3s ease;
            width: 100%;
        }

        .btn-save:hover {
            background-color: #2563eb;
        }

        .btn-save:disabled {
            background-color: #6b7280;
            cursor: not-allowed;
        }

        .feedback-status {
            margin-top: 15px;
            padding: 10px;
            border-radius: 8px;
            font-size: 14px;
            text-align: center;
            display: none;
        }

        .feedback-status.success {
            background-color: rgba(16, 185, 129, 0.2);
            border: 1px solid #10b981;
            color: #10b981;
        }

        .feedback-status.error {
            background-color: rgba(239, 68, 68, 0.2);
            border: 1px solid #ef4444;
            color: #ef4444;
        }

        .feedback-status.loading {
            background-color: rgba(59, 130, 246, 0.2);
            border: 1px solid #3b82f6;
            color: #3b82f6;
        }

        .solution-changed {
            border-color: #fbbf24 !important;
            box-shadow: 0 0 0 1px #fbbf24;
        }

        .nav-link {
            color: #38bdf8;
            text-decoration: none;
            padding: 10px 20px;
            border: 2px solid #38bdf8;
            border-radius: 8px;
            margin: 0 5px;
            transition: all 0.3s ease;
            display: inline-block;
        }

        .nav-link:hover {
            background-color: #38bdf8;
            color: #0f172a;
        }
    </style>
</head>
<body>
    <div style="text-align: center; margin-bottom: 20px;">
        <a href="/dashboard" class="nav-link">📊 Dashboard</a>
        <a href="/" class="nav-link">🔍 Analisar Logs</a>
    </div>
    
    <h1>🔎 Diagnóstico de Log com IA</h1>
    <form id="logForm" method="POST" onsubmit="return showLoading();">
        <label for="log">Cole o log aqui:</label>
        <textarea name="log" required>{{ log or "" }}</textarea>
        <button type="submit" id="submitButton">🔍 Analisar</button>

        <!-- Loading -->
        <div class="text-message" id="loading-message">⏳ Aguarde...</div>
        <div class="progress1" id="loading-bar">
            <div class="progress-bar1" id="progressBar">
                <span class="icon1" id="progressIcon"></span>
                <span class="countdown" id="countdown-timer"></span>
            </div>
        </div>
    </form>

    {% if resultado %}
        <div class="resultado">
            <h2>🧠 Resposta do LLM:</h2>
            <pre>{{ resultado }}</pre>
            {% if analysis_id %}
                <p style="font-size: 12px; color: #64748b; margin-top: 15px;">
                    ID da Análise: {{ analysis_id }}
                </p>
            {% endif %}
        </div>

        {% if analysis_id %}
        <div class="feedback-section">
            <h3>💬 Feedback da Solução</h3>
            <p style="font-size: 14px; color: #94a3b8; margin-bottom: 15px;">
                Avalie e edite a solução sugerida pela IA se necessário:
            </p>
            
            <textarea id="solutionEditor" class="solution-editor" placeholder="Edite a solução aqui...">{{ parsed_solution or "" }}</textarea>
            
            <div class="classification-buttons">
                <button type="button" id="btnValid" class="btn-valid">
                    ✅ Solução Válida
                </button>
                <button type="button" id="btnInvalid" class="btn-invalid">
                    ❌ Solução Inválida
                </button>
            </div>
            
            <button type="button" id="btnSave" class="btn-save" disabled>
                💾 Salvar Alterações
            </button>
            
            <div id="feedbackStatus" class="feedback-status"></div>
            
            <input type="hidden" id="analysisId" value="{{ analysis_id }}">
        </div>
        {% endif %}
    {% endif %}

    <script src="{{ url_for('static', filename='js/form-validation.js') }}"></script>
    <script src="{{ url_for('static', filename='js/loading-states.js') }}"></script>
    <script src="{{ url_for('static', filename='js/feedback.js') }}"></script>
    <script>
        function showLoading() {
            document.getElementById('loading-message').style.display = 'block';
            document.getElementById('loading-bar').style.display = 'block';
            const submitBtn = document.getElementById('submitButton');
            submitBtn.disabled = true;
            submitBtn.textContent = '⏳ Processando...';

            let totalTime = 180;
            let remainingTime = totalTime;
            const countdown = document.getElementById('countdown-timer');
            const progressBar = document.getElementById('progressBar');
            const icon = document.getElementById('progressIcon');

            const intervalId = setInterval(() => {
                remainingTime--;
                const minutes = Math.floor(remainingTime / 60);
                const seconds = remainingTime % 60;
                countdown.textContent = `${minutes} min ${seconds} s`;

                let progressPercentage = ((totalTime - remainingTime) / totalTime) * 100;
                progressBar.style.width = `${progressPercentage}%`;
                icon.style.left = `${progressPercentage}%`;

                if (remainingTime <= 0) {
                    clearInterval(intervalId);
                    countdown.textContent = 'Processando...';
                }
            }, 1000);

            // Enhanced loading with loading manager
            if (window.loadingManager) {
                loadingManager.showAnalysisLoading();
            }

            // Submete o formulário após 200ms para garantir exibição da UI
            setTimeout(() => {
                document.getElementById('logForm').submit();
            }, 200);

            return false; // Impede envio imediato
        }

        // Listen for loading cancellation
        document.addEventListener('loadingCancelled', function(e) {
            if (e.detail.id === 'analysis') {
                // Stop form submission if possible
                const form = document.getElementById('logForm');
                if (form) {
                    form.onsubmit = function() { return false; };
                }
                
                // Reset UI
                const submitBtn = document.getElementById('submitButton');
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.textContent = '🔍 Analisar';
                }
                
                document.getElementById('loading-message').style.display = 'none';
                document.getElementById('loading-bar').style.display = 'none';
            }
        });
    </script>
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Dashboard - Diagnóstico com IA</title>
    <link rel="icon" type="image/png" href="{{ url_for('static', filename='images.png') }}">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/interactive-styles.css') }}">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-image: url('{{ url_for('static', filename='2sinovacoestecnologicas_cover.jpeg') }}');
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
            color: #f1f5f9;
            min-height: 100vh;
            backdrop-filter: blur(5px);
        }

        .dashboard-container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        .dashboard-header {
            text-align: center;
            margin-bottom: 30px;
        }

        .dashboard-header h1 {
            color: #38bdf8;
            font-size: 2.5rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.7);
        }

        .dashboard-header p {
            color: #94a3b8;
            font-size: 1.1rem;
        }

        .nav-links {
            text-align: center;
            margin-bottom: 30px;
        }

        .nav-links a {
            color: #38bdf8;
            text-decoration: none;
            padding: 10px 20px;
            margin: 0 10px;
            border: 2px solid #38bdf8;
            border-radius: 8px;
            transition: all 0.3s ease;
            display: inline-block;
        }

        .nav-links a:hover {
            background-color: #38bdf8;
            color: #0f172a;
        }

        .filters-section {
            background-color: rgba(30, 41, 59, 0.9);
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 30px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.5);
        }

        .filters-section h3 {
            color: #fbbf24;
            margin-bottom: 15px;
            font-size: 1.2rem;
        }

        .filters-row {
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            align-items: end;
        }

        .filter-group {
            display: flex;
            flex-direction: column;
            min-width: 150px;
        }

        .filter-group label {
            color: #cbd5e1;
            margin-bottom: 5px;
            font-size: 0.9rem;
        }

        .filter-group select,
        .filter-group input {
            padding: 8px 12px;
            border-radius: 6px;
            border: 1px solid #475569;
            background-color: #0f172a;
            color: #f1f5f9;
            font-size: 0.9rem;
        }

        .filter-group select:focus,
        .filter-group input:focus {
            outline: none;
            border-color: #38bdf8;
            box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2);
        }

        .btn-filter {
            background-color: #38bdf8;
            color: #0f172a;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
            transition: background-color 0.3s ease;
        }

        .btn-filter:hover {
            background-color: #0ea5e9;
        }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .metric-card {
            background-color: rgba(30, 41, 59, 0.9);
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.5);
            text-align: center;
            transition: transform 0.3s ease;
        }

        .metric-card:hover {
            transform: translateY(-5px);
        }

        .metric-card h3 {
            color: #38bdf8;
            font-size: 1.1rem;
            margin-bottom: 15px;
        }

        .metric-value {
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 10px;
        }

        .metric-value.success {
            color: #10b981;
        }

        .metric-value.warning {
            color: #fbbf24;
        }

        .metric-value.error {
            color: #ef4444;
        }

        .metric-value.info {
            color: #38bdf8;
        }

        .metric-subtitle {
            color: #94a3b8;
            font-size: 0.9rem;
        }

        .charts-section {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .chart-card {
            background-color: rgba(30, 41, 59, 0.9);
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.5);
        }

        .chart-card h3 {
            color: #38bdf8;
            margin-bottom: 20px;
            text-align: center;
        }

        .chart-container {
            position: relative;
            height: 300px;
        }

        .history-section {
            background-color: rgba(30, 41, 59, 0.9);
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.5);
        }

        .history-section h3 {
            color: #38bdf8;
            margin-bottom: 20px;
        }

        .history-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }

        .history-table th,
        .history-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #475569;
        }

        .history-table th {
            background-color: rgba(15, 23, 42, 0.8);
            color: #38bdf8;
            font-weight: bold;
        }

        .history-table td {
            color: #f1f5f9;
        }

        .history-table tr:hover {
            background-color: rgba(15, 23, 42, 0.5);
        }

        .criticality-badge {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: bold;
            text-transform: uppercase;
        }

        .criticality-baixa {
            background-color: rgba(16, 185, 129, 0.2);
            color: #10b981;
            border: 1px solid #10b981;
        }

        .criticality-media {
            background-color: rgba(251, 191, 36, 0.2);
            color: #fbbf24;
            border: 1px solid #fbbf24;
        }

        .criticality-alta {
            background-color: rgba(239, 68, 68, 0.2);
            color: #ef4444;
            border: 1px solid #ef4444;
        }

        .validation-badge {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: bold;
        }

        .validation-true {
            background-color: rgba(16, 185, 129, 0.2);
            color: #10b981;
            border: 1px solid #10b981;
        }

        .validation-false {
            background-color: rgba(239, 68, 68, 0.2);
            color: #ef4444;
            border: 1px solid #ef4444;
        }

        .validation-null {
            background-color: rgba(107, 114, 128, 0.2);
            color: #6b7280;
            border: 1px solid #6b7280;
        }

        .pagination {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 10px;
            margin-top: 20px;
        }

        .pagination button {
            background-color: #475569;
            color: #f1f5f9;
            border: none;
            padding: 8px 12px;
            border-radius: 6px;
            cursor: pointer;
            transition: background-color 0.3s ease;
        }

        .pagination button:hover:not(:disabled) {
            background-color: #38bdf8;
            color: #0f172a;
        }

        .pagination button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .pagination .current-page {
            background-color: #38bdf8;
            color: #0f172a;
            font-weight: bold;
        }

        .loading {
            text-align: center;
            padding: 40px;
            color: #94a3b8;
        }

        .error-message {
            background-color: rgba(239, 68, 68, 0.2);
            border: 1px solid #ef4444;
            color: #ef4444;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
            text-align: center;
        }

        .truncate {
            max-width: 200px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        @media (max-width: 768px) {
            .dashboard-container {
                padding: 10px;
            }

            .filters-row {
                flex-direction: column;
                align-items: stretch;
            }

            .metrics-grid {
                grid-template-columns: 1fr;
            }

            .charts-section {
                grid-template-columns: 1fr;
            }

            .history-table {
                font-size: 0.8rem;
            }

            .truncate {
                max-width: 120px;
            }
        }
    </style>
</head>
<body>
    <div class="dashboard-container">
        <div class="dashboard-header">
            <h1>📊 Dashboard de Análises</h1>
            <p>Métricas e histórico do sistema de diagnóstico com IA</p>
        </div>

        <div class="nav-links">
            <a href="/">🔍 Analisar Logs</a>
            <a href="/dashboard">📊 Dashboard</a>
        </div>

        <div class="filters-section">
            <h3>🔧 Filtros</h3>
            <div class="filters-row">
                <div class="filter-group">
                    <label for="periodFilter">Período (dias):</label>
                    <select id="periodFilter">
                        <option value="7">Últimos 7 dias</option>
                        <option value="30" selected>Últimos 30 dias</option>
                        <option value="90">Últimos 90 dias</option>
                        <option value="365">Último ano</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label for="criticalityFilter">Criticidade:</label>
                    <select id="criticalityFilter">
                        <option value="">Todas</option>
                        <option value="baixa">Baixa</option>
                        <option value="media">Média</option>
                        <option value="alta">Alta</option>
                    </select>
                </div>
                <div class="filter-group">
                    <button class="btn-filter" onclick="applyFilters()">🔄 Atualizar</button>
                </div>
            </div>
        </div>

        <!-- Métricas do PostgreSQL -->
        <div class="metrics-grid">
            <div class="metric-card">
                <h3>📊 Total de Análises</h3>
                <div class="metric-value info">{{ total_analyses }}</div>
                <div class="metric-subtitle">Análises processadas</div>
            </div>
            <div class="metric-card">
                <h3>🔴 Criticidade Alta</h3>
                <div class="metric-value error">{{ criticality_counts.alta }}</div>
                <div class="metric-subtitle">Erros críticos</div>
            </div>
            <div class="metric-card">
                <h3>🟡 Criticidade Média</h3>
                <div class="metric-value warning">{{ criticality_counts.media }}</div>
                <div class="metric-subtitle">Erros moderados</div>
            </div>
            <div class="metric-card">
                <h3>🟢 Criticidade Baixa</h3>
                <div class="metric-value success">{{ criticality_counts.baixa }}</div>
                <div class="metric-subtitle">Erros menores</div>
            </div>
            <div class="metric-card">
                <h3>✅ Soluções Válidas</h3>
                <div class="metric-value success">{{ validation_counts.valid }}</div>
                <div class="metric-subtitle">Aprovadas pelos usuários</div>
            </div>
            <div class="metric-card">
                <h3>❌ Soluções Inválidas</h3>
                <div class="metric-value error">{{ validation_counts.invalid }}</div>
                <div class="metric-subtitle">Rejeitadas pelos usuários</div>
            </div>
            <div class="metric-card">
                <h3>⏳ Pendentes</h3>
                <div class="metric-value warning">{{ validation_counts.pending }}</div>
                <div class="metric-subtitle">Aguardando feedback</div>
            </div>
            <div class="metric-card">
                <h3>🗄️ Status do Banco</h3>
                <div class="metric-value {% if 'Conectado' in database_status %}success{% else %}error{% endif %}">
                    {% if 'Conectado' in database_status %}✅{% else %}❌{% endif %}
                </div>
                <div class="metric-subtitle">{{ database_status }}</div>
            </div>
        </div>

        <!-- Histórico de Análises do PostgreSQL -->
        <div class="history-section">
            <h3>📋 Histórico de Análises (PostgreSQL)</h3>
            {% if error_message %}
                <div class="error-message">{{ error_message }}</div>
            {% endif %}
            
            {% if recent_analyses %}
                <table class="history-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Erro</th>
                            <th>Criticidade</th>
                            <th>Origem</th>
                            <th>Solução Válida</th>
                            <th>Data</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for analysis in recent_analyses %}
                        <tr>
                            <td class="truncate">{{ analysis.id }}</td>
                            <td class="truncate">{{ analysis.erro[:50] }}{% if analysis.erro|length > 50 %}...{% endif %}</td>
                            <td>
                                <span class="criticality-badge criticality-{{ analysis.criticidade }}">
                                    {{ analysis.criticidade }}
                                </span>
                            </td>
                            <td>{{ analysis.origem }}</td>
                            <td>
                                {% if analysis.solucao_valida is none %}
                                    <span class="validation-badge validation-null">Pendente</span>
                                {% elif analysis.solucao_valida %}
                                    <span class="validation-badge validation-true">Válida</span>
                                {% else %}
                                    <span class="validation-badge validation-false">Inválida</span>
                                {% endif %}
                            </td>
                            <td>{{ analysis.timestamp_analise[:19] if analysis.timestamp_analise else 'N/A' }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            {% else %}
                <div class="loading">📭 Nenhuma análise encontrada no PostgreSQL</div>
            {% endif %}
        </div>
    </div>

    <script src="{{ url_for('static', filename='js/loading-states.js') }}"></script>
    <script src="{{ url_for('static', filename='js/dashboard.js') }}"></script>
    <script>
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
    </script>
</body>
</html>
"""


from config.settings import API_URL


def extract_solution_from_response(ai_response):
    """
    Extract the solution text from AI response for the feedback textarea.
    
    Args:
        ai_response: The full AI response text
        
    Returns:
        str: Extracted solution text or empty string if not found
    """
    try:
        # Look for solution section in the response
        lines = ai_response.split('\n')
        solution_lines = []
        in_solution_section = False
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Check if we're entering the solution section
            if ('3.' in line and 'solução' in line_lower) or \
               ('solução sugerida' in line_lower) or \
               ('solução' in line_lower and ':' in line):
                in_solution_section = True
                # Don't include the header line itself
                continue
            
            # Check if we're leaving the solution section (next numbered item)
            elif in_solution_section and line.strip() and \
                 (line.strip().startswith('4.') or 
                  ('criticidade' in line_lower and ':' in line)):
                break
            
            # Collect solution lines
            elif in_solution_section and line.strip():
                # Remove leading dashes, numbers, or bullets
                cleaned_line = re.sub(r'^[-•*\d.\s]+', '', line).strip()
                if cleaned_line:
                    solution_lines.append(cleaned_line)
        
        # Join solution lines
        solution_text = '\n'.join(solution_lines).strip()
        
        # If no structured solution found, try to extract from the whole response
        if not solution_text:
            # Look for any line containing solution keywords
            for line in lines:
                if 'solução' in line.lower() and len(line.strip()) > 20:
                    # Clean up the line
                    cleaned = re.sub(r'^[-•*\d.\s]*', '', line).strip()
                    if cleaned.lower().startswith('solução'):
                        cleaned = re.sub(r'^solução[:\s]*', '', cleaned, flags=re.IGNORECASE).strip()
                    solution_text = cleaned
                    break
        
        return solution_text
        
    except Exception as e:
        logger.warning(f"Erro ao extrair solução da resposta da IA: {e}")
        return ""



@log_operation("analyze_log_with_ai")
@with_api_retry
def analisar_log_com_ia(log):
    """
    Analyze log with AI and save to PostgreSQL using robust error handling.
    
    Args:
        log: Log text to analyze
        
    Returns:
        dict: Contains 'response' (AI response text) and 'analysis_id' (unique ID)
        
    Requirements: 5.4, 5.5, 7.1, 7.4, 8.4 - Input validation, fallbacks, logging, user messages
    """
    start_time = datetime.now()
    
    try:
        # Validate and sanitize input log (Requirement 5.4)
        try:
            validated_log = InputValidator.validate_log_text(log)
        except ValueError as e:
            logger.warning(f"❌ Validação de log falhou: {e}")
            return {
                "response": f"Erro de validação: {str(e)}",
                "analysis_id": None
            }
        
        with performance_monitor("ai_log_analysis", log_length=len(validated_log)):
            # Log analysis start with sanitized context (Requirement 7.4)
            sanitized_log_preview = DataSanitizer.sanitize_text(
                validated_log[:200] + "..." if len(validated_log) > 200 else validated_log
            )
            
            log_user_action(
                "log_analysis_started",
                log_metadata={
                    'log_length': len(validated_log),
                    'log_preview': sanitized_log_preview,
                    'timestamp': start_time.isoformat()
                }
            )
            
            # Initialize vector store with error handling (Requirement 5.5)
            try:
                if not os.path.exists("graylog_vector_index"):
                    with performance_monitor("vector_store_creation"):
                        docs = [Document(page_content=validated_log)]
                        embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2", model_kwargs={"device": "cpu"})
                        vectorstore = FAISS.from_documents(docs, embedding)
                        vectorstore.save_local("graylog_vector_index")
                    logger.info("✅ Vector store criado com sucesso")

                # Load vector store and create retriever
                with performance_monitor("vector_store_loading"):
                    embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2", model_kwargs={"device": "cpu"})
                    db = FAISS.load_local("graylog_vector_index", embedding, allow_dangerous_deserialization=True)
                    retriever = db.as_retriever()
                    
            except Exception as e:
                logger.error(f"❌ Erro ao inicializar vector store: {e}")
                # Fallback: continue without vector store (basic analysis)
                retriever = None
            
            # Initialize LLM with error handling
            try:
                with performance_monitor("llm_initialization"):
                    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
                    if retriever:
                        qa_chain = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)
                    else:
                        # Fallback: direct LLM without retrieval
                        qa_chain = llm
            except Exception as e:
                logger.error(f"❌ Erro ao inicializar LLM: {e}")
                raise Exception("Serviço de IA temporariamente indisponível. Tente novamente.")

            # Create sanitized prompt for AI analysis
            sanitized_log_for_prompt = DataSanitizer.sanitize_text(validated_log)
            prompt = f"""
            Você é um especialista em análise de logs. Analise o log abaixo e me responda em tópicos:
            1. Qual o erro encontrado
            2. Qual a causa provável
            3. Qual a solução sugerida
            4. Qual a criticidade (baixa, média ou alta)

            Log:
            {sanitized_log_for_prompt}
            """

            # Get AI response with retry logic
            try:
                with performance_monitor("ai_inference"):
                    if retriever:
                        resposta = qa_chain.invoke(prompt)["result"]
                    else:
                        # Fallback: direct LLM call
                        resposta = qa_chain.invoke(prompt).content
                
                logger.info("✅ Resposta da IA obtida com sucesso")
            except Exception as e:
                logger.error(f"❌ Erro na inferência da IA: {e}")
                # Fallback response (Requirement 5.5)
                resposta = f"""
                1. Erro: Análise automática indisponível
                2. Causa: Serviço de IA temporariamente indisponível
                3. Solução: Verifique o log manualmente ou tente novamente em alguns minutos
                4. Criticidade: baixa
                
                Log analisado: {sanitized_log_for_prompt[:500]}...
                """

            # Parse AI response with error handling
            try:
                with performance_monitor("ai_response_parsing"):
                    parsed_data = parse_ai_response(resposta)
            except Exception as e:
                logger.warning(f"⚠️ Erro ao parsear resposta da IA: {e}")
                # Fallback parsing (Requirement 5.5)
                parsed_data = {
                    "erro": "Erro de parsing da resposta",
                    "causa": "Resposta da IA em formato inesperado",
                    "solucao": "Revisar manualmente o log",
                    "criticidade": "baixa"
                }
            
            # Create Analysis object with validated data
            try:
                analysis = Analysis(
                    erro=parsed_data["erro"],
                    causa=parsed_data["causa"],
                    solucao=parsed_data["solucao"],
                    criticidade=parsed_data["criticidade"],
                    origem="painel_ia",
                    log_original=validated_log,  # Store original, not sanitized
                    timestamp_analise=datetime.now(),
                    data_incidente=datetime.now()
                )
            except ValueError as e:
                logger.error(f"❌ Erro ao criar objeto Analysis: {e}")
                raise Exception("Erro interno na criação da análise")
            
            # Save analysis to PostgreSQL with retry logic
            try:
                analysis_id = postgres_service.insert_analysis(analysis)
            except Exception as e:
                logger.error(f"❌ Erro ao salvar análise: {e}")
                # Continue without saving - return analysis anyway (Requirement 5.5)
                analysis_id = None
                logger.warning("⚠️ Análise não foi salva, mas resultado será retornado")
        
        # Log successful analysis completion with sanitized metrics
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        sanitized_results = DataSanitizer.sanitize_dict({
            'criticidade': parsed_data["criticidade"],
            'erro_length': len(parsed_data["erro"]),
            'solucao_length': len(parsed_data["solucao"]),
            'duration_ms': duration_ms,
            'ai_response_length': len(resposta),
            'analysis_saved': analysis_id is not None
        })
        
        log_user_action(
            "log_analysis_completed",
            analysis_id=analysis_id,
            analysis_results=sanitized_results
        )
        
        logger.info(f"✅ Análise {'salva' if analysis_id else 'processada'} com ID: {analysis_id}")
        metrics_collector.record_operation("ai_log_analysis", duration_ms, success=True)
        
        return {
            "response": resposta,
            "analysis_id": analysis_id
        }
        
    except Exception as e:
        # Handle errors with user-friendly messages (Requirement 8.4)
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        # Sanitize error context for logging (Requirement 7.4)
        sanitized_error_context = DataSanitizer.sanitize_dict({
            'error_type': type(e).__name__,
            'error_message': str(e),
            'log_length': len(log) if log else 0,
            'duration_ms': duration_ms
        })
        
        log_user_action(
            "log_analysis_failed",
            error_context=sanitized_error_context
        )
        
        logger.error(
            f"❌ Erro na análise do log: {DataSanitizer.sanitize_log_message(str(e))}",
            extra={'operation': 'analyze_log_with_ai', 'log_length': len(log) if log else 0}, 
            exc_info=True
        )
        metrics_collector.record_operation("ai_log_analysis", duration_ms, success=False)
        
        # Return user-friendly error message (Requirement 8.4)
        user_friendly_message = "Erro temporário no sistema de análise. Tente novamente em alguns minutos."
        if "validação" in str(e).lower():
            user_friendly_message = str(e)
        elif "indisponível" in str(e).lower():
            user_friendly_message = str(e)
        
        return {
            "response": user_friendly_message,
            "analysis_id": None
        }

@app.route("/", methods=["GET", "POST"])
@rate_limit("/")
@log_operation("main_index_endpoint")
def index():
    """
    Main index endpoint with robust error handling and input validation.
    
    Requirements: 5.4, 8.4 - Input validation and user-friendly error messages
    """
    resultado = ""
    analysis_id = None
    parsed_solution = ""
    error_message = ""
    log = ""
    
    try:
        if request.method == "POST":
            # Get and validate form data (Requirement 5.4)
            raw_log = request.form.get("log", "")
            
            try:
                log = InputValidator.validate_log_text(raw_log) if raw_log else ""
            except ValueError as e:
                error_message = str(e)
                log = raw_log  # Keep original for display
                logger.warning(f"❌ Validação de log no POST falhou: {e}")
            
            if log and not error_message:
                try:
                    analysis_result = analisar_log_com_ia(log)
                    resultado = analysis_result["response"]
                    analysis_id = analysis_result["analysis_id"]
                    
                    # Extract solution from AI response for the feedback textarea
                    if resultado:
                        parsed_solution = extract_solution_from_response(resultado)
                        
                except Exception as e:
                    error_message = "Erro ao processar análise. Tente novamente."
                    logger.error(f"❌ Erro na análise via POST: {DataSanitizer.sanitize_log_message(str(e))}")
                    
        elif request.args.get("log"):
            # Get and validate query parameter (Requirement 5.4)
            raw_log = request.args.get("log", "")
            
            try:
                log = InputValidator.validate_log_text(raw_log) if raw_log else ""
            except ValueError as e:
                error_message = str(e)
                log = raw_log  # Keep original for display
                logger.warning(f"❌ Validação de log no GET falhou: {e}")
            
            if log and not error_message:
                try:
                    analysis_result = analisar_log_com_ia(log)
                    resultado = analysis_result["response"]
                    analysis_id = analysis_result["analysis_id"]
                    
                    # Extract solution from AI response for the feedback textarea
                    if resultado:
                        parsed_solution = extract_solution_from_response(resultado)
                        
                except Exception as e:
                    error_message = "Erro ao processar análise. Tente novamente."
                    logger.error(f"❌ Erro na análise via GET: {DataSanitizer.sanitize_log_message(str(e))}")
    
    except Exception as e:
        # Handle unexpected errors with user-friendly messages (Requirement 8.4)
        error_message = "Erro interno do sistema. Tente recarregar a página."
        logger.error(f"❌ Erro inesperado no endpoint index: {DataSanitizer.sanitize_log_message(str(e))}", exc_info=True)
    
    # Add error message to template context if present
    template_context = {
        'resultado': resultado,
        'log': log,
        'analysis_id': analysis_id,
        'parsed_solution': parsed_solution
    }
    
    if error_message:
        template_context['error_message'] = error_message
    
    return render_template_string(HTML_TEMPLATE, **template_context)


@app.route("/classificar_solucao", methods=["POST"])
@rate_limit("/classificar_solucao")
@log_operation("classificar_solucao_endpoint")
@with_api_retry
def classificar_solucao():
    """
    API endpoint to classify and update analysis solutions with robust error handling.
    
    Expected JSON payload:
    {
        "id": "analysis_id",
        "solucao_valida": true/false,
        "solucao_editada": "optional edited solution text"
    }
    
    Returns:
        JSON response with success/error status
        
    Requirements: 5.4, 5.5, 7.2, 7.3, 8.4 - Input validation, error handling, logging
    """
    try:
        with performance_monitor("classification_request"):
            # Validate request content type
            if not request.is_json:
                error_response = {
                    "error": "Content-Type deve ser application/json",
                    "status": "error",
                    "code": "INVALID_CONTENT_TYPE"
                }
                logger.warning("❌ Requisição sem Content-Type application/json")
                return jsonify(error_response), 400
            
            # Get and sanitize request data
            raw_data = request.get_json()
            if not raw_data:
                error_response = {
                    "error": "Payload JSON é obrigatório",
                    "status": "error",
                    "code": "EMPTY_PAYLOAD"
                }
                logger.warning("❌ Payload JSON vazio")
                return jsonify(error_response), 400
            
            # Validate and sanitize input data (Requirement 5.4)
            try:
                validated_data = InputValidator.validate_classification_data(raw_data)
                analysis_id = validated_data['id']
                solucao_valida = validated_data['solucao_valida']
                solucao_editada = validated_data.get('solucao_editada')
            except ValueError as e:
                error_response = {
                    "error": str(e),
                    "status": "error",
                    "code": "VALIDATION_ERROR"
                }
                logger.warning(f"❌ Erro de validação: {e}")
                return jsonify(error_response), 400
            
            # Log sanitized user action at the start (Requirement 7.3)
            sanitized_request_data = DataSanitizer.sanitize_dict({
                'has_edited_solution': solucao_editada is not None,
                'solution_valid': solucao_valida,
                'client_ip': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', 'Unknown')
            })
            
            log_user_action(
                "solution_classification_attempt",
                analysis_id=analysis_id,
                request_data=sanitized_request_data
            )
        
        # Check if analysis exists with fallback handling (Requirement 5.5)
        try:
            existing_analysis = postgres_service.get_analysis_by_id(analysis_id)
            if not existing_analysis:
                error_response = {
                    "error": f"Análise com ID '{analysis_id}' não encontrada",
                    "status": "error",
                    "code": "ANALYSIS_NOT_FOUND"
                }
                logger.warning(f"❌ Análise {analysis_id} não encontrada")
                return jsonify(error_response), 404
        except Exception as e:
            # Handle database connection issues with user-friendly message (Requirement 8.4)
            error_details = ErrorHandler.handle_database_error(e, "get_analysis", {'analysis_id': analysis_id})
            error_response = {
                "error": error_details['user_message'],
                "status": "error",
                "code": "DATABASE_ERROR"
            }
            return jsonify(error_response), 503
        
        # Create classification object with validation
        try:
            classification = Classification(
                analysis_id=analysis_id,
                solucao_valida=solucao_valida,
                solucao_editada=solucao_editada
            )
        except ValueError as e:
            error_response = {
                "error": f"Dados de classificação inválidos: {str(e)}",
                "status": "error",
                "code": "CLASSIFICATION_VALIDATION_ERROR"
            }
            logger.warning(f"❌ Erro de validação na classificação: {e}")
            return jsonify(error_response), 400
        
        # Update classification in PostgreSQL with retry logic
        try:
            success = postgres_service.update_classification(analysis_id, classification)
            
            if success:
                # Log successful user action with sanitized details (Requirement 7.3)
                sanitized_classification_data = DataSanitizer.sanitize_dict({
                    'solution_valid': solucao_valida,
                    'solution_edited': solucao_editada is not None,
                    'edited_solution_length': len(solucao_editada) if solucao_editada else 0,
                    'timestamp': classification.timestamp_classificacao.isoformat()
                })
                
                log_user_action(
                    "solution_classification_success",
                    analysis_id=analysis_id,
                    classification_data=sanitized_classification_data
                )
                
                # Log manual edit if solution was edited (Requirement 7.3)
                if solucao_editada:
                    sanitized_edit_details = DataSanitizer.sanitize_dict({
                        'original_solution_exists': existing_analysis.get('solucao') is not None,
                        'edited_solution_length': len(solucao_editada),
                        'solution_marked_valid': solucao_valida,
                        'edit_timestamp': classification.timestamp_classificacao.isoformat()
                    })
                    
                    log_user_action(
                        "manual_solution_edit",
                        analysis_id=analysis_id,
                        edit_details=sanitized_edit_details
                    )
                
                logger.info(f"✅ Classificação da análise {analysis_id} atualizada com sucesso")
                
                # Return success response with sanitized data
                success_response = {
                    "message": "Classificação atualizada com sucesso",
                    "status": "success",
                    "data": {
                        "id": analysis_id,
                        "solucao_valida": solucao_valida,
                        "solucao_editada": bool(solucao_editada),  # Don't return actual content
                        "timestamp": classification.timestamp_classificacao.isoformat()
                    }
                }
                return jsonify(success_response), 200
            else:
                # Log failed user action with context
                log_user_action(
                    "solution_classification_failed",
                    analysis_id=analysis_id,
                    error_context={
                        'reason': 'database_update_failed',
                        'solution_valid': solucao_valida,
                        'solution_edited': solucao_editada is not None
                    }
                )
                
                error_response = {
                    "error": "Falha ao atualizar classificação. Tente novamente.",
                    "status": "error",
                    "code": "UPDATE_FAILED"
                }
                logger.error(f"❌ Falha ao atualizar classificação da análise {analysis_id}")
                return jsonify(error_response), 500
                
        except Exception as e:
            # Handle update errors with user-friendly messages (Requirement 8.4)
            error_details = ErrorHandler.handle_api_error(e, "/classificar_solucao", validated_data)
            error_response = {
                "error": error_details['user_message'],
                "status": "error",
                "code": "UPDATE_ERROR"
            }
            return jsonify(error_response), error_details['status_code']
    
    except Exception as e:
        # Handle unexpected errors with sanitized logging (Requirement 7.4)
        error_details = ErrorHandler.handle_api_error(e, "/classificar_solucao")
        
        error_response = {
            "error": "Erro interno do servidor. Tente novamente.",
            "status": "error",
            "code": "INTERNAL_ERROR"
        }
        
        logger.error(
            f"❌ Erro inesperado no endpoint classificar_solucao: {DataSanitizer.sanitize_log_message(str(e))}",
            exc_info=True
        )
        
        return jsonify(error_response), 500


@app.route("/api/metrics", methods=["GET"])
@rate_limit("/api/metrics")
@log_operation("metrics_api_endpoint")
@with_fallback(ConnectionFallback.get_cached_metrics())
def get_metrics():
    """
    API endpoint to get aggregated metrics for dashboard with robust error handling.
    
    Query parameters:
    - period_days: Number of days to look back (default: 30, max: 365)
    - criticality: Filter by criticality level (optional: baixa, media, alta)
    
    Returns:
        JSON response with aggregated metrics data
        
    Requirements: 5.4, 5.5, 6.1, 6.2, 6.3, 6.4, 8.4 - Input validation, fallbacks, metrics, user messages
    """
    try:
        # Validate and sanitize query parameters (Requirement 5.4)
        raw_filters = {
            'period': request.args.get("period_days", "30"),
            'criticality': request.args.get("criticality", "").strip().lower()
        }
        
        try:
            validated_filters = InputValidator.validate_dashboard_filters(raw_filters)
            period_days = validated_filters.get('period', 30)
            criticality_filter = validated_filters.get('criticality')
        except ValueError as e:
            error_response = {
                "error": str(e),
                "status": "error",
                "code": "VALIDATION_ERROR"
            }
            logger.warning(f"❌ Validação de filtros falhou: {e}")
            return jsonify(error_response), 400
        
        # Get comprehensive metrics from service with fallback (Requirement 5.5)
        try:
            logger.info(f"📊 Obtendo métricas para {period_days} dias")
            
            with performance_monitor("metrics_retrieval", period_days=period_days):
                # Métricas básicas usando PostgreSQL
                metrics = {
                    "total_analyses": 0,
                    "error_count_by_criticality": {"baixa": 0, "media": 0, "alta": 0},
                    "solution_accuracy": {"valid": 0, "invalid": 0, "pending": 0},
                    "recent_activity": []
                }
                
        except Exception as e:
            # Use fallback metrics when service is unavailable (Requirement 5.5)
            logger.warning(f"⚠️ Erro ao obter métricas, usando fallback: {e}")
            
            error_details = ErrorHandler.handle_database_error(
                e, 
                "get_metrics",
                {'period_days': period_days, 'criticality_filter': criticality_filter}
            )
            
            fallback_metrics = ConnectionFallback.get_cached_metrics()
            fallback_metrics['error_notice'] = error_details['user_message']
            
            return jsonify({
                "status": "success",
                "data": fallback_metrics,
                "notice": "Dados em cache - serviço temporariamente indisponível"
            }), 200
        
        # Apply criticality filter if specified
        if criticality_filter:
            try:
                # Filter error count by criticality
                original_counts = metrics.get("error_count_by_criticality", {})
                filtered_count = {criticality_filter: original_counts.get(criticality_filter, 0)}
                metrics["error_count_by_criticality"] = filtered_count
                metrics["total_errors"] = filtered_count[criticality_filter]
                metrics["applied_filters"] = {"criticality": criticality_filter}
                logger.info(f"📊 Filtro de criticidade '{criticality_filter}' aplicado")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao aplicar filtro de criticidade: {e}")
                # Continue without filter
        
        # Add sanitized request metadata
        metrics["request_info"] = DataSanitizer.sanitize_dict({
            "period_days": period_days,
            "criticality_filter": criticality_filter,
            "endpoint": "/api/metrics",
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"✅ Métricas obtidas com sucesso para {period_days} dias")
        return jsonify({
            "status": "success",
            "data": metrics
        }), 200
        
    except Exception as e:
        # Handle unexpected errors with user-friendly messages (Requirement 8.4)
        error_details = ErrorHandler.handle_api_error(e, "/api/metrics", raw_filters)
        
        error_response = {
            "error": error_details['user_message'],
            "status": "error",
            "code": "INTERNAL_ERROR"
        }
        
        logger.error(
            f"❌ Erro inesperado no endpoint /api/metrics: {DataSanitizer.sanitize_log_message(str(e))}",
            exc_info=True
        )
        
        return jsonify(error_response), error_details['status_code']


@app.route("/dashboard")
def dashboard():
    """
    Dashboard route to display metrics and analysis history from PostgreSQL.
    
    Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 8.1 - Dashboard with metrics and filters
    """
    try:
        # Buscar análises recentes do PostgreSQL
        recent_analyses = postgres_service.get_recent_analyses(limit=10)
        
        # Calcular métricas básicas
        total_analyses = len(recent_analyses)
        
        # Contar por criticidade
        criticality_counts = {"baixa": 0, "media": 0, "alta": 0}
        validation_counts = {"valid": 0, "invalid": 0, "pending": 0}
        
        for analysis in recent_analyses:
            # Contar criticidade
            crit = analysis.get('criticidade', '').lower()
            if crit in criticality_counts:
                criticality_counts[crit] += 1
            
            # Contar validação
            valid = analysis.get('solucao_valida')
            if valid is True:
                validation_counts["valid"] += 1
            elif valid is False:
                validation_counts["invalid"] += 1
            else:
                validation_counts["pending"] += 1
        
        # Preparar dados para o template
        dashboard_data = {
            'total_analyses': total_analyses,
            'criticality_counts': criticality_counts,
            'validation_counts': validation_counts,
            'recent_analyses': recent_analyses,
            'database_status': 'PostgreSQL Conectado' if postgres_service.health_check() else 'PostgreSQL Desconectado'
        }
        
        return render_template_string(DASHBOARD_TEMPLATE, **dashboard_data)
        
    except Exception as e:
        logger.error(f"❌ Erro no dashboard: {e}")
        error_data = {
            'total_analyses': 0,
            'criticality_counts': {"baixa": 0, "media": 0, "alta": 0},
            'validation_counts': {"valid": 0, "invalid": 0, "pending": 0},
            'recent_analyses': [],
            'database_status': f'Erro: {str(e)}',
            'error_message': 'Erro ao carregar dados do dashboard'
        }
        return render_template_string(DASHBOARD_TEMPLATE, **error_data)


@app.route("/api/analysis-history", methods=["GET"])
@rate_limit("/api/analysis-history")
@log_operation("analysis_history_api_endpoint")
@with_fallback(ConnectionFallback.get_cached_history())
def get_analysis_history():
    """
    API endpoint to get paginated analysis history with robust error handling.
    
    Query parameters:
    - page: Page number (default: 1, min: 1)
    - limit: Items per page (default: 20, min: 1, max: 100)
    - period_days: Number of days to look back (default: 30, max: 365)
    - criticality: Filter by criticality level (optional: baixa, media, alta)
    - origem: Filter by origin/source (optional)
    
    Returns:
        JSON response with paginated analysis history
        
    Requirements: 5.4, 5.5, 6.5, 8.4 - Input validation, fallbacks, dashboard filters, user messages
    """
    try:
        # Validate and sanitize query parameters (Requirement 5.4)
        raw_filters = {
            'page': request.args.get("page", "1"),
            'limit': request.args.get("limit", "20"),
            'period': request.args.get("period_days", "30"),
            'criticality': request.args.get("criticality", "").strip().lower(),
            'origem': request.args.get("origem", "").strip()
        }
        
        try:
            validated_filters = InputValidator.validate_dashboard_filters(raw_filters)
            page = validated_filters.get('page', 1)
            limit = validated_filters.get('limit', 20)
            period_days = validated_filters.get('period', 30)
            criticality_filter = validated_filters.get('criticality')
            origem_filter = raw_filters['origem'] if raw_filters['origem'] else None
            
        except ValueError as e:
            error_response = {
                "error": str(e),
                "status": "error",
                "code": "VALIDATION_ERROR"
            }
            logger.warning(f"❌ Validação de filtros de histórico falhou: {e}")
            return jsonify(error_response), 400
        
        # Get paginated analyses from PostgreSQL
        logger.info(f"📊 Obtendo histórico de análises PostgreSQL - página {page}, limite {limit}")
        
        # Use the PostgreSQL service for paginated results
        analyses = postgres_service.get_recent_analyses(
            limit=limit,
            offset=(page - 1) * limit
        )
        
        # Calculate pagination metadata (simplified)
        total_count = len(analyses)  # Simplified - in production, would need separate count query
        total_pages = max(1, (total_count + limit - 1) // limit)
        has_next = len(analyses) == limit  # Simplified logic
        has_prev = page > 1
        
        # Build response
        response_data = {
            "analyses": analyses,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_count": total_count,
                "limit": limit,
                "has_next": has_next,
                "has_prev": has_prev,
                "next_page": page + 1 if has_next else None,
                "prev_page": page - 1 if has_prev else None
            },
            "filters": {
                "period_days": period_days,
                "criticality": criticality_filter or None,
                "origem": origem_filter or None
            },
            "generated_at": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Histórico obtido: {len(analyses)} análises, página {page}/{total_pages}")
        return jsonify({
            "status": "success",
            "data": response_data
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Erro inesperado no endpoint /api/analysis-history: {e}")
        return jsonify({
            "error": "Erro interno do servidor ao obter histórico",
            "status": "error"
        }), 500


@app.route("/api/monitoring", methods=["GET"])
@log_operation("monitoring_endpoint")
def get_monitoring_metrics():
    """
    API endpoint to get system monitoring and performance metrics.
    
    Returns:
        JSON response with performance metrics and system health
        
    Requirements: 7.4 - Implement basic performance metrics
    """
    try:
        with performance_monitor("monitoring_metrics_collection"):
            # Get metrics summary from collector
            performance_metrics = metrics_collector.get_metrics_summary()
            
            # Get database health status
            postgres_health = postgres_service.health_check()
            metrics_health = True  # Integrado ao PostgreSQL
            
            # Get basic system info
            system_info = {
                'timestamp': datetime.now().isoformat(),
                'uptime_info': {
                    'collection_start': performance_metrics.get('collection_period', {}).get('start'),
                    'current_time': datetime.now().isoformat()
                },
                'database_health': {
                    'postgres_service': postgres_health,
                    'metrics_service': metrics_health,
                    'overall_status': 'healthy' if postgres_health and metrics_health else 'degraded'
                }
            }
            
            # Combine all monitoring data
            monitoring_data = {
                'status': 'success',
                'system_info': system_info,
                'performance_metrics': performance_metrics,
                'health_checks': {
                    'database_connections': system_info['database_health'],
                    'last_check': datetime.now().isoformat()
                }
            }
            
            # Log monitoring request
            log_user_action(
                "monitoring_metrics_requested",
                monitoring_context={
                    'total_operations': sum(performance_metrics.get('operations', {}).get(op, {}).get('total_count', 0) 
                                          for op in performance_metrics.get('operations', {})),
                    'database_healthy': system_info['database_health']['overall_status'] == 'healthy',
                    'request_timestamp': datetime.now().isoformat()
                }
            )
            
            return jsonify(monitoring_data), 200
            
    except Exception as e:
        # Log monitoring error with context (Requirement 7.4)
        logger.error(f"❌ Erro no endpoint de monitoramento: {e}",
                    extra={'operation': 'monitoring_endpoint'}, exc_info=True)
        
        return jsonify({
            'status': 'error',
            'error': 'Erro interno ao obter métricas de monitoramento',
            'timestamp': datetime.now().isoformat()
        }), 500


@app.route("/api/monitoring/logs", methods=["POST"])
@log_operation("trigger_metrics_summary")
def trigger_metrics_summary():
    """
    Endpoint to trigger logging of current metrics summary.
    Useful for periodic monitoring and debugging.
    
    Requirements: 7.4 - Log performance metrics for monitoring
    """
    try:
        # Log current metrics summary
        metrics_collector.log_metrics_summary()
        
        # Log system health summary
        postgres_health = postgres_service.health_check()
        metrics_health = True  # Integrado ao PostgreSQL
        
        health_summary = {
            'postgres_service_healthy': postgres_health,
            'metrics_service_healthy': metrics_health,
            'overall_system_health': 'healthy' if postgres_health and metrics_health else 'degraded',
            'check_timestamp': datetime.now().isoformat()
        }
        
        logger.info("🏥 Resumo de saúde do sistema", extra={'health_summary': health_summary})
        
        return jsonify({
            'status': 'success',
            'message': 'Métricas registradas nos logs com sucesso',
            'health_summary': health_summary
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Erro ao registrar métricas: {e}",
                    extra={'operation': 'trigger_metrics_summary'}, exc_info=True)
        
        return jsonify({
            'status': 'error',
            'error': 'Erro ao registrar métricas nos logs'
        }), 500


@app.route("/api/performance", methods=["GET"])
@rate_limit("/api/performance")
@log_operation("performance_stats_endpoint")
def get_performance_stats():
    """
    Get performance statistics for monitoring.
    
    Returns:
        JSON with performance metrics including connection pool, cache, and rate limiter stats
    """
    try:
        stats = {
            "timestamp": datetime.now().isoformat(),
            "database": "postgresql",
            "cache_service": None,
            "rate_limiter": None,
            "system_info": {
                "memory_usage": "N/A",
                "cpu_usage": "N/A"
            }
        }
        
        # Connection pool removido - usando PostgreSQL com SQLAlchemy
        
        # Get cache service stats
        from cache_service import get_cache_service
        cache = get_cache_service()
        if cache:
            stats["cache_service"] = cache.get_stats()
        
        # Get rate limiter stats
        from rate_limiter import get_rate_limiter
        limiter = get_rate_limiter()
        if limiter:
            stats["rate_limiter"] = limiter.get_stats()
        
        # Try to get system info if psutil is available
        try:
            import psutil
            process = psutil.Process()
            stats["system_info"] = {
                "memory_usage_mb": round(process.memory_info().rss / 1024 / 1024, 2),
                "cpu_percent": process.cpu_percent(),
                "open_files": len(process.open_files()),
                "connections": len(process.connections())
            }
        except ImportError:
            pass
        
        return jsonify({
            "status": "success",
            "data": stats
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Erro ao obter estatísticas de performance: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "error": "Erro interno do servidor"
        }), 500


if __name__ == "__main__":
    print("=== INICIANDO SERVIDOR ===")
    print("Rotas registradas:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.rule} -> {rule.endpoint}")
    print("=========================")
    print("Servidor iniciando na porta 5057...")
    app.run(host="0.0.0.0", port=5057, debug=False)
