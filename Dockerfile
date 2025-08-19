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
COPY *.md ./

# Criar diretórios necessários
RUN mkdir -p logs graylog_vector_index

EXPOSE 5057
CMD ["python", "painel_ia.py"]
