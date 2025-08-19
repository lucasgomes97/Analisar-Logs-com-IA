# Painel IA - Sistema de Diagnóstico com IA

Sistema web para análise e diagnóstico de logs utilizando Inteligência Artificial.

## 📁 Estrutura do Projeto

```
painel_ia/
├── config/                     # Configurações
│   ├── .env                   # Variáveis de ambiente
│   └── settings.py            # Configurações centralizadas
├── src/                       # Código fonte
│   ├── models/                # Modelos de dados
│   │   ├── __init__.py
│   │   └── models.py          # Classes Analysis e Classification
│   ├── services/              # Serviços
│   │   ├── __init__.py
│   │   ├── cache_service.py   # Serviço de cache
│   │   ├── connection_pool.py # Pool de conexões
│   │   ├── influx_service.py  # Serviço InfluxDB
│   │   ├── metrics_service.py # Serviço de métricas
│   │   ├── query_optimizer.py # Otimizador de queries
│   │   └── rate_limiter.py    # Limitador de taxa
│   └── utils/                 # Utilitários
│       ├── __init__.py
│       ├── error_handling.py  # Tratamento de erros
│       └── logging_config.py  # Configuração de logs
├── static/                    # Arquivos estáticos
│   ├── css/
│   │   └── interactive-styles.css
│   ├── js/
│   │   ├── dashboard.js
│   │   ├── feedback.js
│   │   ├── form-validation.js
│   │   └── loading-states.js
│   ├── 2sinovacoestecnologicas_cover.jpeg
│   ├── images.png
│   └── loading-gif.gif
├── logs/                      # Arquivos de log
├── graylog_vector_index/      # Índice vetorial
│   ├── index.faiss
│   └── index.pkl
├── .kiro/                     # Configurações Kiro
├── Dockerfile                 # Container Docker
├── DASHBOARD_API_DOCS.md      # Documentação da API
├── LOGGING_IMPLEMENTATION.md  # Documentação de logs
├── painel_ia.py              # Aplicação principal
├── requirements.txt          # Dependências Python
└── README.md                 # Este arquivo
```

## 🚀 Como Executar

1. **Instalar dependências:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configurar variáveis de ambiente:**
   - Edite o arquivo `config/.env` com suas credenciais

3. **Executar a aplicação:**
   ```bash
   python painel_ia.py
   ```

4. **Acessar o sistema:**
   - Interface principal: http://localhost:5057
   - Dashboard: http://localhost:5057/dashboard

## 🐳 Docker

```bash
docker build -t painel-ia .
docker run -p 5057:5057 painel-ia
```

## 📊 Funcionalidades

- **Análise de Logs:** Interface para análise de logs com IA
- **Dashboard:** Métricas e histórico de análises
- **Sistema de Feedback:** Validação e correção de soluções da IA
- **Cache Inteligente:** Sistema de cache para melhor performance
- **Pool de Conexões:** Gerenciamento eficiente de conexões
- **Logs Estruturados:** Sistema de logging avançado
- **Rate Limiting:** Controle de taxa de requisições

## 🔧 Tecnologias

- **Backend:** Flask, Python 3.12
- **IA:** OpenAI GPT, LangChain, HuggingFace
- **Banco de Dados:** InfluxDB
- **Cache:** Sistema próprio com TTL
- **Frontend:** HTML5, CSS3, JavaScript
- **Containerização:** Docker