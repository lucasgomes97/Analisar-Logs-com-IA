"""
Configurações específicas para desenvolvimento
"""

# Flask Configuration
DEBUG = True
HOST = "127.0.0.1"
PORT = 5057

# Logging Configuration
LOG_LEVEL = "DEBUG"

# Performance Configuration
CACHE_TTL = 60  # 1 minute for faster development
CACHE_MAX_ENTRIES = 50