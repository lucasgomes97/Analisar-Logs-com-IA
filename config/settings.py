"""
Configurações centralizadas do sistema.
"""
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv('config/.env')

# PostgreSQL Configuration (Primary Database)
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "seu_host")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "SEU_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER", "user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "PASSWORD")

# Database URL for SQLAlchemy
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# InfluxDB removido - migrado para PostgreSQL

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Graylog Configuration
GRAYLOG_URL = os.getenv("GRAYLOG_URL")
GRAYLOG_USER = os.getenv("GRAYLOG_USER")
GRAYLOG_PASSWORD = os.getenv("GRAYLOG_PASSWORD")

# API Configuration
API_URL = "URL DA API"

# Logging Configuration
LOG_LEVEL = "INFO"
LOG_FILE = "logs/feedback_system.log"
ERROR_LOG_FILE = "logs/feedback_system_errors.log"

# Performance Configuration
CACHE_TTL = 300  # 5 minutes
CACHE_MAX_ENTRIES = 100