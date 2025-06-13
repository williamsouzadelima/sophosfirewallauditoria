#!/bin/bash
# setup.sh - Script de instalação e configuração do Strati Audit System

set -e

echo "=========================================="
echo "    Strati Audit System - Setup"
echo "=========================================="
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para logging
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar se é root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_warning "Este script não deve ser executado como root para maior segurança"
        read -p "Continuar mesmo assim? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Verificar dependências do sistema
check_system_deps() {
    log_info "Verificando dependências do sistema..."
    
    # Verificar Python 3
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 não encontrado. Instalando..."
        
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y python3 python3-pip python3-venv
        elif command -v yum &> /dev/null; then
            sudo yum install -y python3 python3-pip
        elif command -v brew &> /dev/null; then
            brew install python3
        else
            log_error "Gerenciador de pacotes não suportado. Instale Python 3 manualmente."
            exit 1
        fi
    fi
    
    # Verificar Git
    if ! command -v git &> /dev/null; then
        log_error "Git não encontrado. Instalando..."
        
        if command -v apt-get &> /dev/null; then
            sudo apt-get install -y git
        elif command -v yum &> /dev/null; then
            sudo yum install -y git
        elif command -v brew &> /dev/null; then
            brew install git
        fi
    fi
    
    # Verificar SSH client
    if ! command -v ssh &> /dev/null; then
        log_warning "SSH client não encontrado. Instalando..."
        
        if command -v apt-get &> /dev/null; then
            sudo apt-get install -y openssh-client
        elif command -v yum &> /dev/null; then
            sudo yum install -y openssh-clients
        fi
    fi
    
    log_success "Dependências do sistema verificadas"
}

# Criar estrutura de diretórios
create_directories() {
    log_info "Criando estrutura de diretórios..."
    
    # Diretórios principais
    mkdir -p {clients,reports,logs,backups,config,scripts}
    mkdir -p data/{databases,temp}
    
    # Permissões seguras
    chmod 750 {clients,reports,logs,backups,config}
    chmod 700 data/databases
    chmod 755 scripts
    
    log_success "Estrutura de diretórios criada"
}

# Configurar ambiente virtual Python
setup_python_env() {
    log_info "Configurando ambiente virtual Python..."
    
    # Criar venv se não existir
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        log_success "Ambiente virtual criado"
    else
        log_info "Ambiente virtual já existe"
    fi
    
    # Ativar venv
    source venv/bin/activate
    
    # Atualizar pip
    pip install --upgrade pip
    
    # Instalar dependências
    if [ -f "requirements.txt" ]; then
        log_info "Instalando dependências Python..."
        pip install -r requirements.txt
        log_success "Dependências instaladas"
    else
        log_warning "Arquivo requirements.txt não encontrado"
    fi
}

# Baixar Sophos Firewall Audit
download_sophos_audit() {
    log_info "Baixando Sophos Firewall Audit..."
    
    if [ ! -d "sophos-firewall-audit" ]; then
        git clone https://github.com/sophos/sophos-firewall-audit.git
        log_success "Sophos Firewall Audit baixado"
    else
        log_info "Sophos Firewall Audit já existe. Atualizando..."
        cd sophos-firewall-audit
        git pull
        cd ..
        log_success "Sophos Firewall Audit atualizado"
    fi
    
    # Verificar se o script principal existe
    if [ -f "sophos-firewall-audit/sophos_firewall_audit.py" ]; then
        chmod +x sophos-firewall-audit/sophos_firewall_audit.py
        log_success "Script Sophos configurado"
    else
        log_warning "Script principal do Sophos não encontrado"
    fi
}

# Configurar banco de dados
setup_database() {
    log_info "Configurando banco de dados..."
    
    # Ativar ambiente virtual
    source venv/bin/activate
    
    # Inicializar banco
    if [ -f "app.py" ]; then
        python3 -c "
from app import init_database
try:
    init_database()
    print('Banco de dados inicializado com sucesso')
except Exception as e:
    print(f'Erro ao inicializar banco: {e}')
    exit(1)
"
        log_success "Banco de dados configurado"
    else
        log_error "Arquivo app.py não encontrado"
        exit 1
    fi
}

# Criar arquivos de configuração
create_config_files() {
    log_info "Criando arquivos de configuração..."
    
    # Arquivo .env
    if [ ! -f ".env" ]; then
        cat > .env << EOF
# Strati Audit System Configuration

# Flask Configuration
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Database
DATABASE_PATH=./data/databases/strati_audit.db

# Sophos Audit
SOPHOS_AUDIT_SCRIPT=./sophos-firewall-audit/sophos_firewall_audit.py

# Security
JWT_EXPIRATION_HOURS=24
BCRYPT_ROUNDS=12

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/strati_audit.log

# Backup
BACKUP_ENABLED=true
BACKUP_INTERVAL_HOURS=6
BACKUP_RETENTION_DAYS=30

# Email Notifications (optional)
SMTP_SERVER=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
ALERT_EMAIL=

# Network
HOST=0.0.0.0
PORT=8080
EOF
        log_success "Arquivo .env criado"
    else
        log_info "Arquivo .env já existe"
    fi
    
    # Arquivo de configuração YAML
    if [ ! -f "config/app_config.yaml" ]; then
        cat > config/app_config.yaml << EOF
# Strati Audit System Configuration

app:
  name: "Strati Audit System"
  version: "1.0.0"
  description: "Sistema de Auditoria Sophos Firewall"

security:
  password_policy:
    min_length: 8
    require_uppercase: true
    require_lowercase: true
    require_numbers: true
    require_symbols: false
  
  session:
    timeout_minutes: 1440  # 24 hours
    max_concurrent: 5

audit:
  default_timeout: 300  # 5 minutes
  max_concurrent_audits: 3
  retry_attempts: 3
  
  checks:
    security_policies: true
    system_configuration: true
    network_settings: true
    user_authentication: true
    logging_configuration: true
    update_status: true
    certificate_validation: true
    intrusion_prevention: true
    web_filtering: true
    application_control: true

reports:
  formats: ["html", "json", "pdf"]
  retention_days: 90
  auto_cleanup: true

monitoring:
  health_check_interval: 300  # 5 minutes
  alert_thresholds:
    failed_audits: 3
    low_score: 60
    critical_findings: 1
EOF
        log_success "Arquivo de configuração criado"
    fi
}

# Criar scripts de serviço
create_service_scripts() {
