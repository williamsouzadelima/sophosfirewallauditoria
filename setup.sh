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
    log_info "Criando scripts de serviço..."
    
    # Script de inicialização
    cat > scripts/start.sh << 'EOF'
#!/bin/bash
# Script de inicialização do Strati Audit System

cd "$(dirname "$0")/.."

# Ativar ambiente virtual
source venv/bin/activate

# Verificar se o banco existe
if [ ! -f "data/databases/strati_audit.db" ]; then
    echo "Inicializando banco de dados..."
    python3 -c "from app import init_database; init_database()"
fi

# Carregar variáveis de ambiente
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Iniciar aplicação
echo "Iniciando Strati Audit System..."
echo "Acesse: http://localhost:${PORT:-8080}"
echo "Usuário padrão: admin / admin123"
echo ""

gunicorn --bind ${HOST:-0.0.0.0}:${PORT:-8080} \
         --workers 4 \
         --worker-class sync \
         --timeout 300 \
         --keepalive 2 \
         --max-requests 1000 \
         --max-requests-jitter 100 \
         --log-level info \
         --access-logfile logs/access.log \
         --error-logfile logs/error.log \
         app:app
EOF
    chmod +x scripts/start.sh
    
    # Script de parada
    cat > scripts/stop.sh << 'EOF'
#!/bin/bash
# Script de parada do Strati Audit System

echo "Parando Strati Audit System..."

# Encontrar processos do gunicorn
pids=$(ps aux | grep '[g]unicorn.*app:app' | awk '{print $2}')

if [ -n "$pids" ]; then
    echo "Parando processos: $pids"
    kill -TERM $pids
    
    # Aguardar 10 segundos
    sleep 10
    
    # Verificar se ainda estão rodando e forçar parada
    pids=$(ps aux | grep '[g]unicorn.*app:app' | awk '{print $2}')
    if [ -n "$pids" ]; then
        echo "Forçando parada dos processos: $pids"
        kill -KILL $pids
    fi
    
    echo "Strati Audit System parado"
else
    echo "Nenhum processo encontrado"
fi
EOF
    chmod +x scripts/stop.sh
    
    # Script de backup
    cat > scripts/backup.sh << 'EOF'
#!/bin/bash
# Script de backup do Strati Audit System

cd "$(dirname "$0")/.."

# Carregar configurações
if [ -f ".env" ]; then
    source .env
fi

BACKUP_DIR="backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="strati_backup_${DATE}.tar.gz"

echo "Iniciando backup..."

# Criar diretório de backup se não existir
mkdir -p $BACKUP_DIR

# Criar backup
tar -czf $BACKUP_DIR/$BACKUP_FILE \
    --exclude='venv' \
    --exclude='sophos-firewall-audit/.git' \
    --exclude='logs/*.log' \
    --exclude='data/temp/*' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    data/ config/ reports/ clients/

if [ $? -eq 0 ]; then
    echo "Backup criado: $BACKUP_DIR/$BACKUP_FILE"
    
    # Limpar backups antigos (manter últimos 30 dias)
    find $BACKUP_DIR -name "strati_backup_*.tar.gz" -mtime +30 -delete
    echo "Backups antigos removidos"
else
    echo "Erro ao criar backup"
    exit 1
fi
EOF
    chmod +x scripts/backup.sh
    
    # Script de restauração
    cat > scripts/restore.sh << 'EOF'
#!/bin/bash
# Script de restauração do Strati Audit System

if [ $# -ne 1 ]; then
    echo "Uso: $0 <arquivo_backup.tar.gz>"
    echo "Backups disponíveis:"
    ls -la backups/strati_backup_*.tar.gz 2>/dev/null || echo "Nenhum backup encontrado"
    exit 1
fi

BACKUP_FILE=$1

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Arquivo de backup não encontrado: $BACKUP_FILE"
    exit 1
fi

echo "Restaurando backup: $BACKUP_FILE"
echo "ATENÇÃO: Esta operação irá sobrescrever os dados atuais!"
read -p "Continuar? (y/N): " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restauração cancelada"
    exit 0
fi

# Parar serviço se estiver rodando
./scripts/stop.sh

# Fazer backup dos dados atuais
if [ -d "data" ]; then
    mv data data_backup_$(date +%Y%m%d_%H%M%S)
fi

# Restaurar backup
tar -xzf "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "Backup restaurado com sucesso"
    echo "Você pode iniciar o sistema com: ./scripts/start.sh"
else
    echo "Erro ao restaurar backup"
    exit 1
fi
EOF
    chmod +x scripts/restore.sh
    
    # Script de atualização
    cat > scripts/update.sh << 'EOF'
#!/bin/bash
# Script de atualização do Strati Audit System

cd "$(dirname "$0")/.."

echo "Atualizando Strati Audit System..."

# Fazer backup antes da atualização
echo "Criando backup de segurança..."
./scripts/backup.sh

# Parar serviço
./scripts/stop.sh

# Ativar ambiente virtual
source venv/bin/activate

# Atualizar Sophos Firewall Audit
if [ -d "sophos-firewall-audit" ]; then
    echo "Atualizando Sophos Firewall Audit..."
    cd sophos-firewall-audit
    git pull
    cd ..
fi

# Atualizar dependências Python
if [ -f "requirements.txt" ]; then
    echo "Atualizando dependências Python..."
    pip install --upgrade -r requirements.txt
fi

# Verificar integridade do banco
echo "Verificando banco de dados..."
python3 -c "
import sqlite3
import os
try:
    if os.path.exists('data/databases/strati_audit.db'):
        conn = sqlite3.connect('data/databases/strati_audit.db')
        conn.execute('PRAGMA integrity_check')
        conn.close()
        print('Banco de dados íntegro')
    else:
        from app import init_database
        init_database()
        print('Banco de dados recriado')
except Exception as e:
    print(f'Erro no banco: {e}')
    exit(1)
"

echo "Atualização concluída!"
echo "Inicie o sistema com: ./scripts/start.sh"
EOF
    chmod +x scripts/update.sh
    
    # Script de monitoramento
    cat > scripts/monitor.sh << 'EOF'
#!/bin/bash
# Script de monitoramento do Strati Audit System

cd "$(dirname "$0")/.."

check_process() {
    pids=$(ps aux | grep '[g]unicorn.*app:app' | awk '{print $2}')
    if [ -n "$pids" ]; then
        return 0
    else
        return 1
    fi
}

check_port() {
    port=${1:-8080}
    if command -v nc >/dev/null 2>&1; then
        nc -z localhost $port >/dev/null 2>&1
        return $?
    else
        curl -s http://localhost:$port >/dev/null 2>&1
        return $?
    fi
}

check_disk_space() {
    usage=$(df . | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ $usage -gt 90 ]; then
        return 1
    else
        return 0
    fi
}

# Verificações
echo "=== Status do Strati Audit System ==="
echo "Data: $(date)"
echo ""

# Verificar processo
if check_process; then
    echo "✅ Processo: Rodando"
else
    echo "❌ Processo: Parado"
fi

# Verificar porta
port=$(grep PORT .env 2>/dev/null | cut -d= -f2 || echo "8080")
if check_port $port; then
    echo "✅ Porta $port: Acessível"
else
    echo "❌ Porta $port: Inacessível"
fi

# Verificar espaço em disco
if check_disk_space; then
    echo "✅ Espaço em disco: OK"
else
    echo "⚠️  Espaço em disco: Baixo (>90%)"
fi

# Verificar arquivos importantes
files=("app.py" "data/databases/strati_audit.db" ".env")
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ Arquivo $file: Existe"
    else
        echo "❌ Arquivo $file: Ausente"
    fi
done

# Verificar logs de erro recentes
if [ -f "logs/error.log" ]; then
    errors=$(tail -n 100 logs/error.log | grep -i error | wc -l)
    if [ $errors -gt 0 ]; then
        echo "⚠️  Logs: $errors erros recentes"
    else
        echo "✅ Logs: Sem erros recentes"
    fi
fi

echo ""
echo "=== Estatísticas ==="

# Estatísticas do banco se disponível
if [ -f "data/databases/strati_audit.db" ]; then
    source venv/bin/activate 2>/dev/null
    python3 -c "
import sqlite3
try:
    conn = sqlite3.connect('data/databases/strati_audit.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM clients WHERE is_active = 1')
    clients = cursor.fetchone()[0]
    print(f'Clientes ativos: {clients}')
    
    cursor.execute('SELECT COUNT(*) FROM firewalls WHERE is_active = 1')
    firewalls = cursor.fetchone()[0]
    print(f'Firewalls cadastrados: {firewalls}')
    
    cursor.execute('SELECT COUNT(*) FROM audits WHERE DATE(started_at) = DATE(\"now\")')
    audits_today = cursor.fetchone()[0]
    print(f'Auditorias hoje: {audits_today}')
    
    cursor.execute('SELECT COUNT(*) FROM audits WHERE status = \"running\"')
    running_audits = cursor.fetchone()[0]
    print(f'Auditorias em execução: {running_audits}')
    
    conn.close()
except Exception as e:
    print(f'Erro ao acessar estatísticas: {e}')
" 2>/dev/null
fi
EOF
    chmod +x scripts/monitor.sh
    
    # Script de instalação de serviço systemd
    cat > scripts/install_service.sh << 'EOF'
#!/bin/bash
# Script para instalar como serviço systemd

if [ "$EUID" -ne 0 ]; then 
    echo "Execute como root para instalar serviço systemd"
    exit 1
fi

INSTALL_DIR=$(pwd)
USER=$(logname)

cat > /etc/systemd/system/strati-audit.service << EOL
[Unit]
Description=Strati Audit System
After=network.target

[Service]
Type=exec
User=$USER
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin
ExecStart=$INSTALL_DIR/venv/bin/gunicorn --bind 0.0.0.0:8080 --workers 4 app:app
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOL

systemctl daemon-reload
systemctl enable strati-audit.service

echo "Serviço instalado!"
echo "Comandos disponíveis:"
echo "  sudo systemctl start strati-audit    # Iniciar"
echo "  sudo systemctl stop strati-audit     # Parar"
echo "  sudo systemctl restart strati-audit  # Reiniciar"
echo "  sudo systemctl status strati-audit   # Status"
EOF
    chmod +x scripts/install_service.sh
    
    log_success "Scripts de serviço criados"
}

# Configurar logs
setup_logging() {
    log_info "Configurando sistema de logs..."
    
    # Criar diretórios de log
    mkdir -p logs
    
    # Criar arquivo de configuração de log
    cat > config/logging.conf << 'EOF'
[loggers]
keys=root,strati

[handlers]
keys=consoleHandler,fileHandler

[formatters]
keys=simpleFormatter,detailedFormatter

[logger_root]
level=INFO
handlers=consoleHandler

[logger_strati]
level=INFO
handlers=consoleHandler,fileHandler
qualname=strati
propagate=0

[handler_consoleHandler]
class=StreamHandler
level=INFO
formatter=simpleFormatter
args=(sys.stdout,)

[handler_fileHandler]
class=handlers.RotatingFileHandler
level=INFO
formatter=detailedFormatter
args=('logs/strati_audit.log', 'a', 10485760, 5)

[formatter_simpleFormatter]
format=%(levelname)s - %(message)s

[formatter_detailedFormatter]
format=%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s
datefmt=%Y-%m-%d %H:%M:%S
EOF
    
    # Configurar logrotate
    if command -v logrotate &> /dev/null; then
        sudo tee /etc/logrotate.d/strati-audit > /dev/null << 'EOF'
/path/to/strati-audit/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 user user
    postrotate
        systemctl reload strati-audit 2>/dev/null || true
    endscript
}
EOF
        # Substitui o path real
        sudo sed -i "s|/path/to/strati-audit|$(pwd)|g" /etc/logrotate.d/strati-audit
    fi
    
    log_success "Sistema de logs configurado"
}

# Configurar firewall
setup_firewall() {
    log_info "Configurando firewall..."
    
    port=${1:-8080}
    
    if command -v ufw &> /dev/null; then
        sudo ufw allow $port/tcp comment "Strati Audit System"
        log_success "Regra UFW adicionada para porta $port"
    elif command -v firewall-cmd &> /dev/null; then
        sudo firewall-cmd --permanent --add-port=$port/tcp
        sudo firewall-cmd --reload
        log_success "Regra FirewallD adicionada para porta $port"
    else
        log_warning "Firewall não detectado. Configure manualmente a porta $port"
    fi
}

# Verificar instalação
verify_installation() {
    log_info "Verificando instalação..."
    
    errors=0
    
    # Verificar arquivos essenciais
    essential_files=(
        "app.py"
        "requirements.txt"
        ".env"
        "venv/bin/activate"
        "data/databases/strati_audit.db"
        "sophos-firewall-audit/sophos_firewall_audit.py"
    )
    
    for file in "${essential_files[@]}"; do
        if [ ! -f "$file" ]; then
            log_error "Arquivo ausente: $file"
            ((errors++))
        fi
    done
    
    # Verificar diretórios
    essential_dirs=(
        "logs"
        "backups"
        "config"
        "scripts"
        "data/databases"
    )
    
    for dir in "${essential_dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            log_error "Diretório ausente: $dir"
            ((errors++))
        fi
    done
    
    # Verificar permissões dos scripts
    scripts_dir="scripts"
    for script in $scripts_dir/*.sh; do
        if [ -f "$script" ] && [ ! -x "$script" ]; then
            log_error "Script sem permissão de execução: $script"
            ((errors++))
        fi
    done
    
    if [ $errors -eq 0 ]; then
        log_success "Instalação verificada com sucesso!"
        return 0
    else
        log_error "Encontrados $errors erros na instalação"
        return 1
    fi
}

# Mostrar informações finais
show_final_info() {
    echo ""
    echo "=========================================="
    echo "    Instalação Concluída!"
    echo "=========================================="
    echo ""
    echo "📁 Diretório de instalação: $(pwd)"
    echo "🐍 Ambiente Python: venv/"
    echo "🗄️  Banco de dados: data/databases/strati_audit.db"
    echo "📊 Sophos Audit: sophos-firewall-audit/"
    echo ""
    echo "🚀 Para iniciar o sistema:"
    echo "   ./scripts/start.sh"
    echo ""
    echo "🛑 Para parar o sistema:"
    echo "   ./scripts/stop.sh"
    echo ""
    echo "📊 Para monitorar o sistema:"
    echo "   ./scripts/monitor.sh"
    echo ""
    echo "💾 Para fazer backup:"
    echo "   ./scripts/backup.sh"
    echo ""
    echo "🔧 Para instalar como serviço:"
    echo "   sudo ./scripts/install_service.sh"
    echo ""
    echo "🌐 Acesso web: http://localhost:8080"
    echo "👤 Usuário padrão: admin"
    echo "🔑 Senha padrão: admin123"
    echo ""
    echo "📚 Documentação: README.md"
    echo "🐛 Logs de erro: logs/error.log"
    echo ""
    log_success "Sistema pronto para uso!"
}

# Função principal
main() {
    echo "Iniciando instalação do Strati Audit System..."
    echo ""
    
    # Verificações iniciais
    check_root
    check_system_deps
    
    # Instalação
    create_directories
    setup_python_env
    download_sophos_audit
    setup_database
    create_config_files
    create_service_scripts
    setup_logging
    
    # Configuração opcional do firewall
    read -p "Configurar firewall automaticamente? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        setup_firewall
    fi
    
    # Verificação final
    if verify_installation; then
        show_final_info
        exit 0
    else
        log_error "Instalação falhou na verificação"
        exit 1
    fi
}

# Executar instalação
main "$@"
