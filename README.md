# 📚 Documentação Completa - Painel IA
## Sistema de Diagnóstico de Logs com Inteligência Artificial

---

## 📖 Índice

1. [Visão Geral](#-visão-geral)
2. [Arquitetura do Sistema](#-arquitetura-do-sistema)
3. [Instalação e Configuração](#-instalação-e-configuração)
4. [Estrutura do Projeto](#-estrutura-do-projeto)
5. [Funcionalidades Principais](#-funcionalidades-principais)
6. [API Endpoints](#-api-endpoints)
7. [Modelos de Dados](#-modelos-de-dados)
8. [Serviços e Componentes](#-serviços-e-componentes)
9. [Monitoramento e Logging](#-monitoramento-e-logging)
10. [Sistema de Feedback](#-sistema-de-feedback)
11. [Dashboard e Métricas](#-dashboard-e-métricas)
12. [Tratamento de Erros](#-tratamento-de-erros)
13. [Performance e Otimização](#-performance-e-otimização)
14. [Segurança](#-segurança)
15. [Docker e Deploy](#-docker-e-deploy)
16. [Troubleshooting](#-troubleshooting)
17. [Roadmap](#-roadmap)

---

## 🎯 Visão Geral

O **Painel IA** é um sistema web avançado para análise automatizada de logs utilizando Inteligência Artificial. O sistema oferece diagnóstico inteligente de erros, sugestões de soluções e um sistema de feedback para melhoria contínua.

### 🎯 Objetivos Principais

- **Automatizar** a análise de logs complexos
- **Acelerar** o processo de diagnóstico de problemas
- **Melhorar** a precisão das soluções através de feedback
- **Monitorar** performance e métricas do sistema
- **Fornecer** interface intuitiva para análise

### 🚀 Características Técnicas

- **Backend**: Flask (Python 3.12)
- **Frontend**: HTML5, CSS3, JavaScript (SPA)
- **IA**: OpenAI GPT-3.5-turbo, LangChain
- **Banco de Dados**: PostgreSQL com SQLAlchemy
- **Embeddings**: HuggingFace all-MiniLM-L6-v2
- **Vector Store**: FAISS para busca semântica
- **Containerização**: Docker

---

## 🏗️ Arquitetura do Sistema

### 📊 Diagrama de Arquitetura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Flask API     │    │   PostgreSQL    │
│   (HTML/JS)     │◄──►│   (Python)      │◄──►│   Database      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   OpenAI API    │
                       │   (GPT-3.5)     │
                       └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   FAISS Vector  │
                       │   Store         │
                       └─────────────────┘
```

### 🔄 Fluxo de Processamento

1. **Entrada**: Usuário insere log no frontend
2. **Validação**: Sistema valida e sanitiza entrada
3. **Embeddings**: Texto é convertido para vetores
4. **Vector Store**: Busca semântica por logs similares
5. **IA**: OpenAI analisa log e gera diagnóstico
6. **Armazenamento**: Resultado salvo no PostgreSQL
7. **Feedback**: Usuário pode validar/editar solução
8. **Métricas**: Sistema coleta dados de performance

---

## ⚙️ Instalação e Configuração

### 📋 Pré-requisitos

- Python 3.12+
- PostgreSQL 12+
- Chave API OpenAI
- Docker (opcional)
- 4GB RAM mínimo
- 2GB espaço em disco

### 🔧 Instalação Local

1. **Clone o repositório**:
   ```bash
   git clone <repository-url>
   cd painel_ia
   ```

2. **Instale dependências**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure variáveis de ambiente**:
   ```bash
   cp config/.env.example config/.env
   ```

4. **Edite o arquivo `.env`**:
   ```bash
   # PostgreSQL Configuration
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_DB=analise_logs
   POSTGRES_USER=seu_usuario
   POSTGRES_PASSWORD=sua_senha

   # OpenAI Configuration
   OPENAI_API_KEY=sk-sua-chave-api

   # Graylog Configuration (Opcional)
   GRAYLOG_URL=https://seu-graylog.com
   GRAYLOG_USER=usuario
   GRAYLOG_PASSWORD=senha
   ```

5. **Execute o sistema**:
   ```bash
   python painel_ia.py
   ```

6. **Acesse a aplicação**:
   - Interface principal: http://localhost:5057
   - Dashboard: http://localhost:5057/dashboard

### 🐳 Instalação via Docker

1. **Build da imagem**:
   ```bash
   docker build -t painel-ia .
   ```

2. **Execute o container**:
   ```bash
   docker run -p 5057:5057 \
     -e POSTGRES_HOST=seu_host \
     -e POSTGRES_USER=seu_usuario \
     -e POSTGRES_PASSWORD=sua_senha \
     -e OPENAI_API_KEY=sua_chave \
     painel-ia
   ```

---

## 📁 Estrutura do Projeto

```
painel_ia/
├── 📁 config/                     # Configurações
│   ├── .env                      # Variáveis de ambiente
│   ├── settings.py               # Configurações centralizadas
│   ├── development.py            # Config desenvolvimento
│   └── production.py             # Config produção
├── 📁 src/                       # Código fonte
│   ├── 📁 models/                # Modelos de dados
│   │   ├── __init__.py
│   │   ├── models.py             # Classes principais
│   │   └── postgres_models.py    # Modelos SQLAlchemy
│   ├── 📁 services/              # Serviços
│   │   ├── __init__.py
│   │   ├── postgres_service.py   # Serviço PostgreSQL
│   │   ├── cache_service.py      # Serviço de cache
│   │   ├── metrics_service.py    # Métricas (integrado)
│   │   ├── query_optimizer.py    # Otimizador
│   │   └── rate_limiter.py       # Rate limiting
│   └── 📁 utils/                 # Utilitários
│       ├── __init__.py
│       ├── error_handling.py     # Tratamento de erros
│       └── logging_config.py     # Configuração de logs
├── 📁 static/                    # Arquivos estáticos
│   ├── 📁 css/
│   │   └── interactive-styles.css
│   ├── 📁 js/
│   │   ├── dashboard.js
│   │   ├── feedback.js
│   │   ├── form-validation.js
│   │   └── loading-states.js
│   └── 📁 images/               # Imagens e assets
├── 📁 logs/                     # Arquivos de log
├── 📁 graylog_vector_index/     # Índice vetorial
│   ├── index.faiss
│   └── index.pkl
├── 📄 Dockerfile               # Container Docker
├── 📄 requirements.txt         # Dependências Python
├── 📄 painel_ia.py            # Aplicação principal
└── 📄 README.md               # Documentação básica
```

---

## ✨ Funcionalidades Principais

### 🔍 Análise Inteligente de Logs

**Características:**
- Análise automatizada via OpenAI GPT-3.5-turbo
- Busca semântica com embeddings HuggingFace
- Identificação de erro, causa e solução
- Classificação de criticidade (baixa/média/alta)
- Cache inteligente para performance

**Processo:**
1. Usuário insere log no textarea
2. Sistema valida e sanitiza entrada
3. Log é processado via LangChain
4. IA gera análise estruturada
5. Resultado é salvo no PostgreSQL

### 📊 Dashboard Interativo

**Métricas Disponíveis:**
- Total de análises processadas
- Distribuição por criticidade
- Taxa de validação de soluções
- Histórico de análises
- Status do sistema

**Filtros:**
- Período temporal (7, 30, 90, 365 dias)
- Criticidade específica
- Origem dos erros

### 💬 Sistema de Feedback

**Funcionalidades:**
- Validação de soluções (válida/inválida)
- Edição de soluções sugeridas
- Histórico de modificações
- Métricas de precisão da IA

---

## 🌐 API Endpoints

### 🏠 Endpoints Principais

#### `GET/POST /`
**Interface Principal**
- **Método**: GET, POST
- **Descrição**: Interface principal para análise de logs
- **Parâmetros POST**: `log` (texto do log)
- **Resposta**: HTML com resultado da análise

#### `GET /dashboard`
**Dashboard de Métricas**
- **Método**: GET
- **Descrição**: Interface do dashboard com métricas
- **Resposta**: HTML com dashboard interativo

### 🔧 API Endpoints

#### `POST /classificar_solucao`
**Classificar Solução**
- **Método**: POST
- **Content-Type**: application/json
- **Payload**:
  ```json
  {
    "id": "uuid-da-analise",
    "solucao_valida": true,
    "solucao_editada": "Solução editada (opcional)"
  }
  ```
- **Resposta**:
  ```json
  {
    "status": "success",
    "message": "Classificação atualizada com sucesso",
    "data": {
      "id": "uuid",
      "solucao_valida": true,
      "timestamp": "2025-01-01T12:00:00"
    }
  }
  ```

#### `GET /api/metrics`
**Métricas do Sistema**
- **Método**: GET
- **Parâmetros Query**:
  - `period_days`: Período em dias (default: 30)
  - `criticality`: Filtro por criticidade
- **Resposta**:
  ```json
  {
    "status": "success",
    "data": {
      "total_analyses": 150,
      "error_count_by_criticality": {
        "baixa": 80,
        "media": 50,
        "alta": 20
      },
      "solution_accuracy": {
        "valid": 120,
        "invalid": 15,
        "pending": 15
      }
    }
  }
  ```

#### `GET /api/analysis-history`
**Histórico de Análises**
- **Método**: GET
- **Parâmetros Query**:
  - `page`: Número da página (default: 1)
  - `limit`: Itens por página (default: 20)
  - `period_days`: Período em dias
  - `criticality`: Filtro por criticidade
- **Resposta**: JSON com histórico paginado

#### `GET /api/monitoring`
**Métricas de Monitoramento**
- **Método**: GET
- **Descrição**: Métricas de performance e saúde do sistema
- **Resposta**: JSON com métricas de sistema

#### `GET /api/performance`
**Estatísticas de Performance**
- **Método**: GET
- **Descrição**: Stats detalhados de cache, pool, rate limiter
- **Resposta**: JSON com estatísticas

---

## 📋 Modelos de Dados

### 🗂️ Analysis Model

```python
@dataclass
class Analysis:
    id: str                          # UUID único
    erro: str                        # Descrição do erro
    causa: str                       # Causa identificada
    solucao: str                     # Solução sugerida
    criticidade: str                 # baixa|media|alta
    origem: str                      # Origem do log
    log_original: str               # Log original
    solucao_valida: Optional[str]   # true|false|null
    solucao_editada: Optional[str]  # Solução editada
    timestamp_analise: datetime     # Timestamp análise
    data_incidente: datetime        # Data do incidente
```

### 🗂️ Classification Model

```python
@dataclass
class Classification:
    analysis_id: str                    # UUID da análise
    solucao_valida: bool               # Solução válida?
    solucao_editada: Optional[str]     # Solução editada
    timestamp_classificacao: datetime  # Timestamp classificação
```

### 🗄️ PostgreSQL Schema

```sql
CREATE TABLE tb_analise_logs (
    id_analise VARCHAR(36) NOT NULL,
    data_incidente TIMESTAMP WITH TIME ZONE NOT NULL,
    erro TEXT NOT NULL,
    causa TEXT NOT NULL,
    solucao TEXT NOT NULL,
    criticidade VARCHAR(10) NOT NULL,
    origem VARCHAR(255) NOT NULL,
    log_original TEXT NOT NULL,
    solucao_valida BOOLEAN,
    solucao_editada TEXT,
    timestamp_analise TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id_analise, data_incidente)
);
```

---

## 🔧 Serviços e Componentes

### 🐘 PostgreSQL Service

**Responsabilidades:**
- Conexão com banco PostgreSQL
- CRUD de análises
- Queries otimizadas
- Health checks
- Pool de conexões SQLAlchemy

**Principais Métodos:**
- `insert_analysis()`: Insere nova análise
- `get_analysis_by_id()`: Busca por ID
- `update_classification()`: Atualiza feedback
- `get_recent_analyses()`: Lista análises recentes
- `health_check()`: Verifica saúde do banco

### 💾 Cache Service

**Características:**
- Cache em memória com TTL
- Eviction policy LRU
- Estatísticas de hit/miss
- Thread-safe operations

**Configurações:**
- `CACHE_TTL`: 300 segundos (padrão)
- `CACHE_MAX_ENTRIES`: 100 entradas (padrão)

### ⚡ Rate Limiter

**Funcionalidades:**
- Rate limiting por endpoint
- Window-based limiting
- IP-based restrictions
- Configurável por rota

**Limites Padrão:**
- `/`: 10 requests/minuto
- `/api/*`: 30 requests/minuto

### 🎯 Query Optimizer

**Otimizações:**
- Query caching
- Index suggestions
- Performance monitoring
- Query plan analysis

---

## 📊 Monitoramento e Logging

### 📝 Sistema de Logging

**Níveis de Log:**
- `DEBUG`: Desenvolvimento e debugging
- `INFO`: Operações normais
- `WARNING`: Situações de atenção
- `ERROR`: Erros recuperáveis
- `CRITICAL`: Erros críticos

**Estrutura de Logs:**
```python
{
    "timestamp": "2025-01-01T12:00:00Z",
    "level": "INFO",
    "operation": "analyze_log_with_ai",
    "user_id": "anonymous",
    "request_id": "uuid",
    "metadata": {
        "log_length": 1500,
        "duration_ms": 2500,
        "success": true
    }
}
```

### 📈 Métricas de Performance

**Métricas Coletadas:**
- Tempo de resposta por endpoint
- Taxa de sucesso/erro
- Uso de cache (hit/miss ratio)
- Conexões de banco ativas
- Memória e CPU utilizadas

**Endpoints de Métricas:**
- `/api/monitoring`: Métricas gerais
- `/api/performance`: Stats detalhados
- `/api/monitoring/logs`: Trigger de logs

### 🏥 Health Checks

**Verificações:**
- Conectividade PostgreSQL
- Status da API OpenAI
- Disponibilidade de serviços
- Integridade do cache

---

## 💬 Sistema de Feedback

### ✅ Validação de Soluções

**Processo:**
1. IA gera solução inicial
2. Usuário visualiza no frontend
3. Usuário marca como válida/inválida
4. Opcionalmente edita a solução
5. Feedback salvo no PostgreSQL
6. Métricas atualizadas

### 📝 Edição de Soluções

**Características:**
- Editor de texto in-line
- Detecção de mudanças
- Preservação do original
- Histórico de edições

**Interface:**
```html
<textarea id="solutionEditor" class="solution-editor">
  Solução sugerida pela IA...
</textarea>
<button class="btn-valid">✅ Solução Válida</button>
<button class="btn-invalid">❌ Solução Inválida</button>
<button class="btn-save">💾 Salvar Alterações</button>
```

### 📊 Métricas de Precisão

**KPIs Calculados:**
- Taxa de soluções válidas
- Taxa de edição manual
- Tempo médio de validação
- Distribuição por criticidade

---

## 📊 Dashboard e Métricas

### 📈 Componentes do Dashboard

**Cartões de Métricas:**
- Total de Análises
- Erros por Criticidade
- Taxa de Validação
- Status do Sistema

**Tabela de Histórico:**
- ID da análise
- Erro identificado
- Criticidade
- Status de validação
- Timestamp

**Filtros Avançados:**
- Período temporal
- Criticidade específica
- Origem dos logs
- Status de validação

### 🔄 Atualização em Tempo Real

**Tecnologias:**
- JavaScript fetch API
- Polling automático
- Loading states
- Error handling

**Intervalo de Atualização:**
- Métricas: 30 segundos
- Histórico: 60 segundos
- Status: 15 segundos

---

## ❌ Tratamento de Erros

### 🛡️ Estratégias de Error Handling

**1. Input Validation**
```python
class InputValidator:
    @staticmethod
    def validate_log_text(log_text: str) -> str:
        if not log_text or not log_text.strip():
            raise ValueError("Log não pode estar vazio")
        if len(log_text) > 50000:
            raise ValueError("Log muito extenso (máx: 50.000 chars)")
        return log_text.strip()
```

**2. Fallback Mechanisms**
```python
@with_fallback(ConnectionFallback.get_cached_metrics())
def get_metrics():
    try:
        return postgres_service.get_metrics()
    except Exception:
        return fallback_value
```

**3. Retry Logic**
```python
@with_api_retry
def call_openai_api(prompt):
    # Retenta até 3 vezes com backoff exponencial
    pass
```

### 🚨 Códigos de Erro

**API Error Codes:**
- `VALIDATION_ERROR`: Erro de validação de entrada
- `DATABASE_ERROR`: Erro de conexão com banco
- `AI_SERVICE_ERROR`: Erro na API OpenAI
- `RATE_LIMIT_EXCEEDED`: Limite de taxa excedido
- `INTERNAL_ERROR`: Erro interno do sistema

**HTTP Status Codes:**
- `400`: Bad Request (validação)
- `429`: Too Many Requests (rate limit)
- `500`: Internal Server Error
- `503`: Service Unavailable

---

## ⚡ Performance e Otimização

### 🚀 Otimizações Implementadas

**1. Cache Inteligente**
- Cache de respostas da IA
- Cache de embeddings
- Cache de métricas
- TTL configurável

**2. Connection Pooling**
- Pool SQLAlchemy otimizado
- Reconexão automática
- Health checks periódicos

**3. Query Optimization**
- Índices otimizados
- Queries paginadas
- Lazy loading

**4. Resource Management**
- Memory management
- CPU optimization
- Disk I/O otimizado

### 📊 Benchmarks

**Performance Targets:**
- Análise de log: < 5 segundos
- Dashboard load: < 2 segundos
- API response: < 1 segundo
- Cache hit ratio: > 80%

**Métricas Monitoradas:**
- Response time percentiles (p50, p95, p99)
- Throughput (requests/second)
- Error rate (%)
- Resource utilization

---

## 🔒 Segurança

### 🛡️ Medidas de Segurança

**1. Input Sanitization**
```python
class DataSanitizer:
    @staticmethod
    def sanitize_text(text: str) -> str:
        # Remove caracteres perigosos
        # Escapa HTML/SQL
        # Trunca se necessário
        return cleaned_text
```

**2. Rate Limiting**
- Prevenção de DoS
- Rate limiting por IP
- Throttling inteligente

**3. Data Validation**
- Validação de tipos
- Sanitização de SQL
- Escape de HTML

**4. Logging Seguro**
- Sanitização de logs
- Não exposição de dados sensíveis
- Audit trail completo

### 🔐 Configurações de Segurança

**Environment Variables:**
- Chaves API em variáveis de ambiente
- Conexões seguras (TLS)
- Timeouts apropriados

**Database Security:**
- Conexões criptografadas
- Least privilege principle
- SQL injection prevention

---

## 🐳 Docker e Deploy

### 📦 Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fonte
COPY src/ ./src/
COPY config/ ./config/
COPY static/ ./static/
COPY painel_ia.py .

# Criar diretórios necessários
RUN mkdir -p logs graylog_vector_index

EXPOSE 5057
CMD ["python", "painel_ia.py"]
```

### 🚀 Deploy Production

**1. Build e Push**
```bash
# Build da imagem
docker build -t painel-ia:latest .

# Tag para registry
docker tag painel-ia:latest registry/painel-ia:latest

# Push para registry
docker push registry/painel-ia:latest
```

**2. Deploy com Docker Compose**
```yaml
version: '3.8'
services:
  painel-ia:
    image: registry/painel-ia:latest
    ports:
      - "5057:5057"
    environment:
      - POSTGRES_HOST=postgres
      - POSTGRES_DB=analise_logs
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - OPENAI_API_KEY=${OPENAI_KEY}
    depends_on:
      - postgres
  
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=analise_logs
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

**3. Configuração de Produção**
- Uso do arquivo `config/production.py`
- SSL/TLS habilitado
- Logs estruturados
- Monitoramento ativo

### ☁️ Deploy em Cloud

**AWS ECS/Fargate:**
- Task definition otimizada
- Load balancer configurado
- Auto scaling habilitado
- CloudWatch integration

**Kubernetes:**
- Deployment manifests
- Service discovery
- Config maps
- Health checks

---

## 🔧 Troubleshooting

### 🚨 Problemas Comuns

**1. Erro de Conexão PostgreSQL**
```
Erro: connection to server at "localhost" (127.0.0.1), port 5432 failed
```
**Solução:**
- Verificar se PostgreSQL está rodando
- Validar credenciais no `.env`
- Verificar firewall/network

**2. OpenAI API Error**
```
Erro: You exceeded your current quota
```
**Solução:**
- Verificar quota da API OpenAI
- Validar chave API
- Implementar retry logic

**3. Vector Store Error**
```
Erro: No such file or directory: 'graylog_vector_index'
```
**Solução:**
- Criar diretório: `mkdir graylog_vector_index`
- Regenerar índice vetorial

**4. Memory Issues**
```
Erro: MemoryError during embedding
```
**Solução:**
- Aumentar RAM disponível
- Otimizar batch size
- Limpar cache regularmente

### 🔍 Debugging

**1. Habilitar Debug Logging**
```python
# config/development.py
LOG_LEVEL = "DEBUG"
```

**2. Verificar Health Endpoints**
```bash
curl http://localhost:5057/api/monitoring
curl http://localhost:5057/api/performance
```

**3. Monitorar Logs**
```bash
tail -f logs/feedback_system.log
tail -f logs/feedback_system_errors.log
```

**4. Verificar Métricas**
```bash
# PostgreSQL connections
SELECT count(*) FROM pg_stat_activity;

# Sistema de cache
curl http://localhost:5057/api/performance | jq '.cache_service'
```

---

## 🗺️ Roadmap

### 📅 Próximas Versões

**v2.0 - AI Enhancement**
- [ ] Integração com modelos locais (Llama/Mistral)
- [ ] Fine-tuning com dados históricos
- [ ] Multi-modal analysis (logs + métricas)
- [ ] Auto-classification de tipos de erro

**v2.1 - Advanced Analytics**
- [ ] Análise de tendências temporais
- [ ] Detecção de anomalias
- [ ] Correlação entre sistemas
- [ ] Alertas preditivos

**v2.2 - Enterprise Features**
- [ ] Multi-tenancy
- [ ] SSO/SAML integration
- [ ] Role-based access control
- [ ] Advanced audit logging

**v2.3 - Integration & Automation**
- [ ] Webhook notifications
- [ ] Slack/Teams integration
- [ ] CI/CD pipeline integration
- [ ] Auto-remediation triggers

### 🎯 Melhorias Técnicas

**Performance:**
- [ ] Async processing com Celery
- [ ] Database sharding
- [ ] CDN para assets estáticos
- [ ] GraphQL API

**Observabilidade:**
- [ ] OpenTelemetry integration
- [ ] Prometheus metrics
- [ ] Grafana dashboards
- [ ] Distributed tracing

**ML/AI:**
- [ ] Model versioning
- [ ] A/B testing para modelos
- [ ] Feedback loop automatizado
- [ ] Custom embeddings

---

## 📞 Suporte

### 🆘 Como Obter Ajuda

**1. Documentação**
- README.md principal
- Documentação inline no código
- Comments detalhados

**2. Logs do Sistema**
- `logs/feedback_system.log`
- `logs/feedback_system_errors.log`

**3. Monitoring Endpoints**
- `/api/monitoring` - métricas gerais
- `/api/performance` - stats detalhados

**4. Health Checks**
- PostgreSQL: `postgres_service.health_check()`
- Cache: `cache_service.get_stats()`
- Rate Limiter: `rate_limiter.get_stats()`

### 🐛 Reportar Bugs

**Informações Necessárias:**
- Versão do sistema
- Stack trace completo
- Logs relevantes
- Passos para reproduzir
- Ambiente (dev/staging/prod)

### 💡 Sugestões

**Canais:**
- Issues no repositório
- Discussions para ideias
- Pull requests para contribuições

---

## 📜 Licença

Este projeto está sob licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

---

## 👥 Contribuidores

Desenvolvido por **@lucasgomes97**.

### 🤝 Como Contribuir

1. Fork o projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

---

**© 2025 Lucas Gomes - Sistema Painel IA**
