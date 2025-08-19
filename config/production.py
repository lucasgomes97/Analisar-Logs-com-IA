"""
Configurações específicas para produção
"""

# Flask Configuration
DEBUG = False
HOST = "0.0.0.0"
PORT = 5057

# Logging Configuration
LOG_LEVEL = "INFO"

# Performance Configuration
CACHE_TTL = 600  # 10 minutes
CACHE_MAX_ENTRIES = 200

# Security Configuration
SECRET_KEY = "your-secret-key-here"  # Altere em produção