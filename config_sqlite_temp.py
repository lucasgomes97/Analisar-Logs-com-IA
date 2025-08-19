#!/usr/bin/env python3
"""
Configuração temporária usando SQLite para desenvolvimento
Use este arquivo enquanto o PostgreSQL não estiver acessível
"""
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv('config/.env')

# Configurações SQLite temporárias
SQLITE_DB_PATH = "temp_analise_logs.db"
DATABASE_URL = f"sqlite:///{SQLITE_DB_PATH}"

# Outras configurações (mantém as originais)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GRAYLOG_URL = os.getenv("GRAYLOG_URL")
GRAYLOG_USER = os.getenv("GRAYLOG_USER")
GRAYLOG_PASSWORD = os.getenv("GRAYLOG_PASSWORD")

# API Configuration
API_URL = "link da sua API"

# Logging Configuration
LOG_LEVEL = "INFO"
LOG_FILE = "logs/feedback_system.log"
ERROR_LOG_FILE = "logs/feedback_system_errors.log"

# Performance Configuration
CACHE_TTL = 300  # 5 minutes
CACHE_MAX_ENTRIES = 100

print("⚠️ USANDO CONFIGURAÇÃO TEMPORÁRIA COM SQLITE")
print(f"📁 Banco SQLite: {SQLITE_DB_PATH}")
print(f"🔗 DATABASE_URL: {DATABASE_URL}")
print()
print("Para voltar ao PostgreSQL:")
print("1. Resolva o problema do pg_hba.conf")
print("2. Use novamente config/settings.py")