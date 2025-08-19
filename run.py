#!/usr/bin/env python3
"""
Script de inicialização do Painel IA
"""
import sys
import os

# Adiciona o diretório raiz ao path para imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importa e executa a aplicação principal
from painel_ia import app

if __name__ == "__main__":
    print("🚀 Iniciando Painel IA - Sistema de Diagnóstico com IA")
    print("📊 Dashboard disponível em: http://localhost:5057/dashboard")
    print("🔍 Interface principal em: http://localhost:5057")
    print("=" * 60)
    
    app.run(
        host="0.0.0.0",
        port=5057,
        debug=False
    )