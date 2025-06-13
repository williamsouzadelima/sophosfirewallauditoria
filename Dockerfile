# Strati Audit System - Dockerfile
# Imagem base Python otimizada
FROM python:3.11-slim

# Informações do container
LABEL maintainer="Strati Security Team <contato@strati.com.br>"
LABEL version="1.0.0"
LABEL description="Sistema de Auditoria Sophos Firewall"

# Definir argumentos de build
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

# Labels padrão
LABEL org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.name="Strati Audit System" \
      org.label-schema.description="Sistema de Auditoria Sophos Firewall" \
      org.label-schema.url="https://strati.com.br" \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.vcs-url="https://github.com/strati-security/strati-audit-system" \
      org.label-schema.vendor="Strati Security" \
      org.label-schema.version=$VERSION \
      org.label-schema.schema-version="1.0"

# Variáveis de ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FLASK_ENV=production \
    FLASK_DEBUG=False \
    HOST=0.0.0.0 \
    PORT=8080

# Criar usuário não-root para segurança
RUN groupadd -r strati && useradd -r -g strati -d /app -s /bin/bash strati

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build essentials
    build-essential \
    gcc \
    g++ \
    # Network tools
    openssh-client \
    curl \
    wget \
    telnet \
    # Version control
    git \
    # System utilities
    procps \
    vim \
    nano \
    # Timezone data
    tzdata \
    # SSL certificates
    ca-certificates \
    # Cleanup
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Configurar timezone
ENV TZ=America/Sao_Paulo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Criar estrutura de diretórios
WORKDIR /app

# Criar diretórios necessários
RUN mkdir -p \
    /app/data/databases \
    /app/data/temp \
    /app/logs \
    /app/reports \
    /app/clients \
    /app/backups \
    /app/config \
    /app/scripts

# Copiar requirements primeiro para cache de Docker layers
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn[gevent]

# Copiar arquivos da aplicação
COPY . .

# Baixar Sophos Firewall Audit se não existir
RUN if [ ! -d "sophos-firewall-audit" ]; then \
        git clone https://github.com/sophos/sophos-firewall-audit.git && \
        chmod +x sophos-firewall-audit/sophos_firewall_audit.py; \
    fi

# Copiar e configurar scripts
COPY scripts/ ./scripts/
RUN chmod +x scripts/*.sh

# Criar arquivo .env padrão se não existir
RUN if [ ! -f ".env" ]; then \
        cp .env.example .env && \
        sed -i "s/your-secret-key-here-generate-a-secure-one/$(python -c 'import secrets; print(secrets.token_hex(32))')/g" .env; \
    fi

# Configurar permissões
RUN chown -R strati:strati /app && \
    chmod 755 /app && \
    chmod -R 750 /app/data /app/logs /app/reports /app/clients /app/backups /app/config && \
    chmod -R 755 /app/scripts

# Criar script de inicialização
RUN cat > /app/docker-entrypoint.sh << 'EOF'
#!/bin/bash
set -e

echo "=============================================="
echo "🛡️  Strati Audit System - Starting Container"
echo "=============================================="

# Função para logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Verificar se é primeira execução
if [ ! -f "/app/data/databases/strati_audit.db" ]; then
    log "🗄️  Primeira execução detectada. Inicializando banco de dados..."
    python -c "from app import init_database; init_database()"
    log "✅ Banco de dados inicializado"
fi

# Verificar integridade do banco
log "🔍 Verificando integridade do banco de dados..."
python -c "
import sqlite3
import os
try:
    if os.path.exists('/app/data/databases/strati_audit.db'):
        conn = sqlite3.connect('/app/data/databases/strati_audit.db')
        result = conn.execute('PRAGMA integrity_check').fetchone()
        conn.close()
        if result[0] != 'ok':
            raise Exception('Database integrity check failed')
        print('✅ Banco de dados íntegro')
    else:
        raise Exception('Database file not found')
except Exception as e:
    print(f'❌ Erro no banco: {e}')
    exit(1)
"

# Verificar script Sophos
if [ -f "/app/sophos-firewall-audit/sophos_firewall_audit.py" ]; then
    log "✅ Script Sophos Firewall Audit encontrado"
else
    log "⚠️  Script Sophos não encontrado. Algumas funcionalidades podem ser limitadas."
fi

# Mostrar informações de inicialização
log "📊 Informações do container:"
log "   • Usuário: $(whoami)"
log "   • Diretório: $(pwd)"
log "   • Python: $(python --version)"
log "   • Host: ${HOST:-0.0.0.0}"
log "   • Porta: ${PORT:-8080}"
log "   • Ambiente: ${FLASK_ENV:-production}"

# Verificar se é comando especial
case "${1:-}" in
    bash|sh)
        log "🐚 Iniciando shell interativo..."
        exec "$@"
        ;;
    python)
        log "🐍 Executando comando Python..."
        shift
        exec python "$@"
        ;;
    backup)
        log "💾 Executando backup..."
        exec /app/scripts/backup.sh
        ;;
    restore)
        log "🔄 Executando restauração..."
        shift
        exec /app/scripts/restore.sh "$@"
        ;;
    monitor)
        log "📊 Executando monitor..."
        exec /app/scripts/monitor.sh
        ;;
    *)
        # Comando padrão: iniciar aplicação
        log "🚀 Iniciando Strati Audit System..."
        log "🌐 Acesse: http://localhost:${PORT:-8080}"
        log "👤 Usuário padrão: admin / admin123"
        echo "=============================================="
        
        # Iniciar aplicação com Gunicorn
        exec gunicorn \
            --bind ${HOST:-0.0.0.0}:${PORT:-8080} \
            --workers ${WORKERS:-4} \
            --worker-class ${WORKER_CLASS:-sync} \
            --timeout ${WORKER_TIMEOUT:-300} \
            --keepalive ${KEEPALIVE:-2} \
            --max-requests ${MAX_REQUESTS:-1000} \
            --max-requests-jitter ${MAX_REQUESTS_JITTER:-100} \
            --log-level ${LOG_LEVEL:-info} \
            --access-logfile /app/logs/access.log \
            --error-logfile /app/logs/error.log \
            --capture-output \
            --enable-stdio-inheritance \
            app:app
        ;;
esac
EOF

# Tornar script executável
RUN chmod +x /app/docker-entrypoint.sh

# Mudar para usuário não-root
USER strati

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/api/health || exit 1

# Expor porta
EXPOSE 8080

# Volumes para persistência
VOLUME ["/app/data", "/app/logs", "/app/reports", "/app/backups"]

# Entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Comando padrão
CMD ["gunicorn"]

# Build hooks (para Docker Hub)
# ARG BUILD_DATE
# ARG VCS_REF
# RUN echo "Build Date: $BUILD_DATE" > /app/build-info.txt && \
#     echo "VCS Ref: $VCS_REF" >> /app/build-info.txt
