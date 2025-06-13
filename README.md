# Strati Audit System 🛡️

Sistema de auditoria de segurança para firewalls Sophos, desenvolvido para automatizar e centralizar auditorias de segurança em infraestruturas empresariais.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Security](https://img.shields.io/badge/Security-Audit-red.svg)

## 📋 Índice

- [Características](#-características)
- [Pré-requisitos](#-pré-requisitos)
- [Instalação Rápida](#-instalação-rápida)
- [Instalação Manual](#-instalação-manual)
- [Configuração](#-configuração)
- [Uso](#-uso)
- [API](#-api)
- [Integração Sophos](#-integração-sophos)
- [Segurança](#-segurança)
- [Monitoramento](#-monitoramento)
- [Backup e Recuperação](#-backup-e-recuperação)
- [Solução de Problemas](#-solução-de-problemas)
- [Contribuição](#-contribuição)

## 🚀 Características

### Core Features
- ✅ **Auditoria Automatizada**: Integração com [Sophos Firewall Audit](https://github.com/sophos/sophos-firewall-audit)
- 🎯 **Multi-Cliente**: Gerenciamento de múltiplos clientes e firewalls
- 📊 **Dashboard Interativo**: Interface web moderna e responsiva
- 📈 **Relatórios Detalhados**: Geração automática de relatórios HTML/JSON
- 🔐 **Autenticação JWT**: Sistema seguro de autenticação
- 📱 **Mobile Friendly**: Interface otimizada para dispositivos móveis

### Security Features
- 🛡️ **Análise de Políticas**: Verificação de políticas de segurança
- 🔍 **Configuração do Sistema**: Auditoria de configurações críticas
- 🌐 **Configurações de Rede**: Análise de configurações de rede
- 👤 **Autenticação de Usuários**: Verificação de configurações de usuário
- 📝 **Configuração de Logs**: Auditoria de configurações de logging
- 🔄 **Status de Atualizações**: Verificação de atualizações de sistema
- 📜 **Validação de Certificados**: Verificação de certificados SSL/TLS
- 🚫 **Prevenção de Intrusão**: Análise de sistemas IPS
- 🌐 **Filtro Web**: Verificação de configurações de filtro web
- 📱 **Controle de Aplicações**: Auditoria de controle de aplicações

### Management Features
- 👥 **Gerenciamento de Usuários**: Sistema de roles e permissões
- 📊 **Métricas de Performance**: Acompanhamento de scores de segurança
- 🔄 **Execução Agendada**: Auditorias programadas
- 💾 **Backup Automático**: Sistema de backup automatizado
- 📧 **Alertas por Email**: Notificações automáticas
- 🔍 **Logs Detalhados**: Sistema de logging abrangente

## 📋 Pré-requisitos

### Sistema Operacional
- Linux (Ubuntu 20.04+, CentOS 8+, RHEL 8+)
- macOS 10.15+
- Windows 10+ (via WSL2)

### Software
```bash
# Essenciais
python3 (3.8+)
python3-pip
python3-venv
git
openssh-client

# Opcionais
docker
nginx (para produção)
postgresql (para produção)
```

### Recursos de Sistema
```
RAM: 2GB mínimo, 4GB recomendado
CPU: 2 cores mínimo
Disco: 10GB espaço livre
Rede: Acesso SSH aos firewalls Sophos
```

### Acesso aos Firewalls
- Usuário administrativo nos firewalls Sophos
- Acesso SSH habilitado (porta 4444 padrão)
- Conectividade de rede entre o sistema e os firewalls

## 🚀 Instalação Rápida

### Método 1: Script Automatizado (Recomendado)

```bash
# 1. Clonar o repositório
git clone https://github.com/seu-usuario/strati-audit-system.git
cd strati-audit-system

# 2. Executar instalação automatizada
chmod +x setup.sh
./setup.sh

# 3. Iniciar o sistema
./scripts/start.sh
```

### Método 2: Docker (Mais Simples)

```bash
# 1. Clonar e construir
git clone https://github.com/seu-usuario/strati-audit-system.git
cd strati-audit-system

# 2. Construir imagem
docker build -t strati-audit .

# 3. Executar container
docker run -d \
  --name strati-audit \
  -p 8080:8080 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  strati-audit
```

## 🔧 Instalação Manual

### 1. Preparar Ambiente

```bash
# Clonar repositório
git clone https://github.com/seu-usuario/strati-audit-system.git
cd strati-audit-system

# Criar estrutura de diretórios
mkdir -p {clients,reports,logs,backups,config,scripts}
mkdir -p data/{databases,temp}
```

### 2. Configurar Python

```bash
# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Baixar Sophos Firewall Audit

```bash
# Clonar repositório oficial
git clone https://github.com/sophos/sophos-firewall-audit.git
chmod +x sophos-firewall-audit/sophos_firewall_audit.py
```

### 4. Configurar Banco de Dados

```bash
# Ativar ambiente virtual
source venv/bin/activate

# Inicializar banco
python3 -c "from app import init_database; init_database()"
```

### 5. Configurar Variáveis de Ambiente

```bash
# Criar arquivo .env
cp .env.example .env
nano .env
```

### 6. Iniciar Sistema

```bash
# Método desenvolvimento
python3 app.py

# Método produção
gunicorn --bind 0.0.0.0:8080 --workers 4 app:app
```

## ⚙️ Configuração

### Arquivo .env

```bash
# Flask Configuration
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=sua_chave_secreta_aqui

# Database
DATABASE_PATH=./data/databases/strati_audit.db

# Sophos Audit
SOPHOS_AUDIT_SCRIPT=./sophos-firewall-audit/sophos_firewall_audit.py

# Security
JWT_EXPIRATION_HOURS=24
BCRYPT_ROUNDS=12

# Network
HOST=0.0.0.0
PORT=8080

# Email (opcional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=seu_email@gmail.com
SMTP_PASSWORD=sua_senha_app
ALERT_EMAIL=admin@empresa.com
```

### Configuração de Usuários

O sistema vem com usuários padrão:

```
Usuário: admin
Senha: admin123
Role: admin

```

**⚠️ IMPORTANTE**: Altere as senhas padrão imediatamente após a instalação!

### Configuração de Firewalls

1. Acesse o dashboard web
2. Clique em "Novo Cliente"
3. Preencha os dados do cliente
4. Adicione os firewalls com:
   - Hostname/IP
   - Porta SSH (geralmente 4444)
   - Credenciais de acesso

## 📖 Uso

### Dashboard Web

Acesse: `http://localhost:8080`

#### Funcionalidades Principais:

1. **Gerenciamento de Clientes**
   - Adicionar novos clientes
   - Configurar firewalls por cliente
   - Visualizar estatísticas

2. **Execução de Auditorias**
   - Auditorias sob demanda
   - Seleção de cliente específico
   - Monitoramento em tempo real

3. **Relatórios**
   - Visualização online
   - Download em HTML
   - Histórico de auditorias

4. **Monitoramento**
   - Dashboard com métricas
   - Scores de segurança
   - Alertas automáticos

### Scripts de Linha de Comando

```bash
# Iniciar sistema
./scripts/start.sh

# Parar sistema
./scripts/stop.sh

# Monitorar sistema
./scripts/monitor.sh

# Fazer backup
./scripts/backup.sh

# Restaurar backup
./scripts/restore.sh backup_file.tar.gz

# Atualizar sistema
./scripts/update.sh

# Instalar como serviço
sudo ./scripts/install_service.sh
```

### Execução via API

```python
import requests

# Login
response = requests.post('http://localhost:8080/api/auth/login', 
                        json={'username': 'admin', 'password': 'admin123'})
token = response.json()['token']

# Executar auditoria
headers = {'Authorization': f'Bearer {token}'}
response = requests.post('http://localhost:8080/api/audits/run',
                        json={'client_id': 1}, 
                        headers=headers)

audit_id = response.json()['audit_id']
print(f"Auditoria iniciada: {audit_id}")
```

## 🔌 API

### Autenticação

```bash
# Login
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

### Clientes

```bash
# Listar clientes
curl -X GET http://localhost:8080/api/clients \
  -H "Authorization: Bearer TOKEN"

# Criar cliente
curl -X POST http://localhost:8080/api/clients \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Empresa ABC",
    "description": "Cliente teste",
    "firewalls": [
      {
        "hostname": "192.168.1.1",
        "port": 4444,
        "username": "admin"
      }
    ]
  }'
```

### Auditorias

```bash
# Executar auditoria
curl -X POST http://localhost:8080/api/audits/run \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"client_id": 1}'

# Listar auditorias
curl -X GET http://localhost:8080/api/audits \
  -H "Authorization: Bearer TOKEN"
```

### Relatórios

```bash
# Listar relatórios
curl -X GET http://localhost:8080/api/reports \
  -H "Authorization: Bearer TOKEN"

# Download relatório
curl -X GET http://localhost:8080/api/reports/audit_1/download \
  -H "Authorization: Bearer TOKEN" \
  -o relatorio.html
```

## 🛡️ Integração Sophos

O sistema utiliza o projeto oficial [Sophos Firewall Audit](https://github.com/sophos/sophos-firewall-audit) para realizar as auditorias.

### Verificações Realizadas

1. **Políticas de Segurança**
   - Regras de firewall
   - Políticas de acesso
   - Configurações de NAT

2. **Configuração do Sistema**
   - Configurações administrativas
   - Configurações de tempo
   - Configurações de SNMP

3. **Segurança de Rede**
   - Configurações de interface
   - VPN settings
   - Wireless security

4. **Autenticação**
   - Configurações de usuário
   - Integração LDAP/AD
   - Políticas de senha

5. **Logging e Monitoramento**
   - Configurações de syslog
   - Alertas de segurança
   - Retenção de logs

### Personalização de Verificações

```python
# Exemplo de configuração personalizada
audit_config = {
    'checks': {
        'security_policies': True,
        'system_configuration': True,
        'network_settings': False,  # Desabilitar
        'user_authentication': True,
        'logging_configuration': True,
        # ... outras verificações
    }
}
```

## 🔐 Segurança

### Autenticação e Autorização

- **JWT Tokens**: Autenticação baseada em tokens
- **Bcrypt**: Hash seguro de senhas
- **Role-based Access**: Sistema de permissões por função
- **Session Management**: Controle de sessões ativas

### Proteção de Dados

- **Criptografia**: Credenciais criptografadas no banco
- **SSL/TLS**: Suporte para conexões seguras
- **Input Validation**: Validação rigorosa de entradas
- **SQL Injection Protection**: Prepared statements

### Boas Práticas

```bash
# 1. Alterar senhas padrão
# 2. Configurar SSL/TLS em produção
# 3. Usar banco PostgreSQL em produção
# 4. Configurar firewall adequadamente
# 5. Manter sistema atualizado
# 6. Monitorar logs regularmente
# 7. Fazer backups regulares
```

### Configuração SSL/TLS

```nginx
# Configuração Nginx para produção
server {
    listen 443 ssl;
    server_name seu-dominio.com;
    
    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;
    
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 📊 Monitoramento

### Métricas do Sistema

```bash
# Status geral
./scripts/monitor.sh

# Logs em tempo real
tail -f logs/strati_audit.log

# Performance do banco
sqlite3 data/databases/strati_audit.db ".schema"
```

### Alertas Automáticos

O sistema pode enviar alertas por email para:

- Falhas em auditorias
- Scores baixos de segurança
- Problemas técnicos
- Atualizações importantes

### Health Checks

```bash
# Verificar se aplicação está respondendo
curl -f http://localhost:8080/api/health || echo "Sistema indisponível"

# Verificar banco de dados
sqlite3 data/databases/strati_audit.db "PRAGMA integrity_check;"
```

## 💾 Backup e Recuperação

### Backup Automático

```bash
# Configurar backup automático (crontab)
0 2 * * * /path/to/strati-audit/scripts/backup.sh

# Backup manual
./scripts/backup.sh
```

### Restauração

```bash
# Listar backups disponíveis
ls -la backups/

# Restaurar backup específico
./scripts/restore.sh backups/strati_backup_20231201_020000.tar.gz
```

### Estratégia de Backup

1. **Backup Diário**: Dados completos às 02:00
2. **Backup Incremental**: A cada 6 horas
3. **Retenção**: 30 dias para backups locais
4. **Backup Remoto**: Configuração opcional

## 🐛 Solução de Problemas

### Problemas Comuns

#### 1. Erro de Conexão com Firewall

```bash
# Verificar conectividade
telnet IP_FIREWALL 4444

# Testar SSH
ssh -p 4444 admin@IP_FIREWALL

# Verificar logs
tail -f logs/strati_audit.log | grep -i error
```

#### 2. Banco de Dados Corrompido

```bash
# Verificar integridade
sqlite3 data/databases/strati_audit.db "PRAGMA integrity_check;"

# Reparar se necessário
./scripts/restore.sh backup_recente.tar.gz
```

#### 3. Problemas de Autenticação

```bash
# Resetar senha admin
python3 -c "
from app import *
import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect('data/databases/strati_audit.db')
cursor = conn.cursor()
new_password = generate_password_hash('nova_senha')
cursor.execute('UPDATE users SET password_hash = ? WHERE username = ?', 
               (new_password, 'admin'))
conn.commit()
conn.close()
print('Senha alterada com sucesso')
"
```

#### 4. Performance Lenta

```bash
# Verificar recursos do sistema
top
df -h
free -m

# Otimizar banco de dados
sqlite3 data/databases/strati_audit.db "VACUUM;"
```

### Logs de Debug

```bash
# Ativar modo debug
export FLASK_DEBUG=True

# Logs detalhados
tail -f logs/strati_audit.log logs/error.log

# Logs de acesso
tail -f logs/access.log
```

### Suporte

Para suporte técnico:

1. Verificar logs de erro
2. Executar script de diagnóstico: `./scripts/monitor.sh`
3. Coletar informações do sistema
4. Abrir issue no GitHub com detalhes

## 🤝 Contribuição

### Como Contribuir

1. **Fork** o repositório
2. **Clone** seu fork localmente
3. Crie uma **branch** para sua feature
4. **Commit** suas mudanças
5. **Push** para sua branch
6. Abra um **Pull Request**

### Desenvolvimento

```bash
# Configurar ambiente de desenvolvimento
git clone https://github.com/seu-usuario/strati-audit-system.git
cd strati-audit-system

# Instalar dependências de desenvolvimento
pip install -r requirements-dev.txt

# Executar testes
pytest

# Verificar código
flake8 app.py
black app.py
```

### Padrões de Código

- **Python**: PEP 8
- **JavaScript**: ESLint
- **CSS**: Prettier
- **Commits**: Conventional Commits

### Estrutura do Projeto

```
strati-audit-system/
├── app.py                 # Aplicação principal
├── sophos_audit_integration.py  # Integração Sophos
├── requirements.txt       # Dependências Python
├── setup.sh              # Script de instalação
├── .env.example          # Exemplo de configuração
├── README.md             # Documentação
├── scripts/              # Scripts de automação
│   ├── start.sh
│   ├── stop.sh
│   ├── monitor.sh
│   └── backup.sh
├── config/               # Arquivos de configuração
├── data/                 # Dados do sistema
│   └── databases/
├── logs/                 # Logs do sistema
├── reports/              # Relatórios gerados
├── backups/              # Backups do sistema
└── sophos-firewall-audit/ # Projeto oficial Sophos
```

## 📝 Changelog

### v1.0.0 (2023-12-01)
- ✨ Lançamento inicial
- 🛡️ Integração com Sophos Firewall Audit
- 📊 Dashboard web responsivo
- 🔐 Sistema de autenticação JWT
- 📈 Geração de relatórios HTML
- 👥 Gerenciamento multi-cliente
- 💾 Sistema de backup automatizado

## 📄 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 📞 Contato

- **Autor**: Strati Security Team
- **Email**: contato@strati.com.br
- **Website**: https://strati.com.br
- **GitHub**: https://github.com/strati-security

## 🙏 Agradecimentos

- **Sophos**: Pelo projeto open source [Sophos Firewall Audit](https://github.com/sophos/sophos-firewall-audit)
- **Flask Team**: Pelo excelente framework web
- **Comunidade Python**: Pelas bibliotecas utilizadas
- **Contribuidores**: Todos que ajudaram no desenvolvimento

---

**⚠️ Aviso de Segurança**: Este sistema lida com informações sensíveis de segurança. Use sempre em ambientes seguros e mantenha-o atualizado.

**📚 Documentação Adicional**: Para mais detalhes técnicos, consulte a [Wiki do projeto](https://github.com/seu-usuario/strati-audit-system/wiki).
