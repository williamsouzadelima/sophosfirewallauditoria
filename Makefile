# Strati Audit System - Makefile
# Automação de tarefas para desenvolvimento e produção

# Configurações
PROJECT_NAME := strati-audit
VERSION := 1.0.0
PYTHON := python3
PIP := pip3
VENV := venv
DOCKER_IMAGE := strati-audit:latest
DOCKER_CONTAINER := strati-audit-app

# Cores para output
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
BLUE := \033[0;34m
NC := \033[0m # No Color

# Arquivos importantes
REQUIREMENTS := requirements.txt
ENV_FILE := .env
ENV_EXAMPLE := .env.example

.PHONY: help install clean dev prod docker test lint format backup restore

# Target padrão
.DEFAULT_GOAL := help

# ==============================================
# COMANDOS DE AJUDA
# ==============================================

help: ## Mostrar esta ajuda
	@echo "$(GREEN)Strati Audit System - Comandos Disponíveis$(NC)"
	@echo "=============================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(BLUE)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Exemplos de uso:$(NC)"
	@echo "  make install    # Instalar dependências"
	@echo "  make dev        # Executar em modo desenvolvimento"
	@echo "  make prod       # Executar em modo produção"
	@echo "  make docker     # Construir e executar com Docker"
	@echo "  make test       # Executar testes"
	@echo "  make backup     # Fazer backup do sistema"

# ==============================================
# COMANDOS DE INSTALAÇÃO E CONFIGURAÇÃO
# ==============================================

install: ## Instalar dependências e configurar ambiente
	@echo "$(GREEN)Instalando Strati Audit System...$(NC)"
	@if [ ! -d "$(VENV)" ]; then \
		echo "$(YELLOW)Criando ambiente virtual...$(NC)"; \
		$(PYTHON) -m venv $(VENV); \
	fi
	@echo "$(YELLOW)Ativando ambiente virtual e instalando dependências...$(NC)"
	@. $(VENV)/bin/activate && \
		$(PIP) install --upgrade pip setuptools wheel && \
		$(PIP) install -r $(REQUIREMENTS)
	@echo "$(YELLOW)Criando estrutura de diretórios...$(NC)"
	@mkdir -p {data/databases,logs,reports,clients,backups,config,scripts}
	@echo "$(YELLOW)Configurando arquivo .env...$(NC)"
	@if [ ! -f "$(ENV_FILE)" ]; then \
		cp $(ENV_EXAMPLE) $(ENV_FILE); \
		echo "$(GREEN)Arquivo .env criado. Configure as variáveis necessárias!$(NC)"; \
	fi
	@echo "$(YELLOW)Baixando Sophos Firewall Audit...$(NC)"
	@if [ ! -d "sophos-firewall-audit" ]; then \
		git clone https://github.com/sophos/sophos-firewall-audit.git; \
		chmod +x sophos-firewall-audit/sophos_firewall_audit.py; \
	fi
	@echo "$(YELLOW)Inicializando banco de dados...$(NC)"
	@. $(VENV)/bin/activate && $(PYTHON) -c "from app import init_database; init_database()"
	@echo "$(GREEN)✅ Instalação concluída!$(NC)"
	@echo "$(BLUE)Execute 'make dev' para iniciar em modo desenvolvimento$(NC)"

setup: install ## Alias para install

clean: ## Limpar arquivos temporários e cache
	@echo "$(YELLOW)Limpando arquivos temporários...$(NC)"
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .pytest_cache
	@rm -rf .coverage
	@rm -rf htmlcov
	@rm -rf build
	@rm -rf dist
	@rm -f strati_audit.pid
	@echo "$(GREEN)✅ Limpeza concluída$(NC)"

clean-all: clean ## Limpar tudo incluindo venv
	@echo "$(YELLOW)Removendo ambiente virtual...$(NC)"
	@rm -rf $(VENV)
	@echo "$(GREEN)✅ Limpeza completa concluída$(NC)"

# ==============================================
# COMANDOS DE EXECUÇÃO
# ==============================================

dev: ## Executar em modo desenvolvimento
	@echo "$(GREEN)Iniciando Strati Audit em modo desenvolvimento...$(NC)"
	@if [ ! -f "$(ENV_FILE)" ]; then \
		echo "$(RED)❌ Arquivo .env não encontrado. Execute 'make install' primeiro.$(NC)"; \
		exit 1; \
	fi
	@. $(VENV)/bin/activate && $(PYTHON) run.py --dev

prod: ## Executar em modo produção
	@echo "$(GREEN)Iniciando Strati Audit em modo produção...$(NC)"
	@if [ ! -f "$(ENV_FILE)" ]; then \
		echo "$(RED)❌ Arquivo .env não encontrado. Execute 'make install' primeiro.$(NC)"; \
		exit 1; \
	fi
	@. $(VENV)/bin/activate && $(PYTHON) run.py

run: dev ## Alias para dev

start: ## Iniciar serviço usando scripts
	@echo "$(GREEN)Iniciando serviço...$(NC)"
	@./scripts/start.sh

stop: ## Parar serviço
	@echo "$(YELLOW)Parando serviço...$(NC)"
	@./scripts/stop.sh

restart: stop start ## Reiniciar serviço

status: ## Verificar status do sistema
	@echo "$(BLUE)Status do Strati Audit System:$(NC)"
	@./scripts/monitor.sh

# ==============================================
# COMANDOS DOCKER
# ==============================================

docker-build: ## Construir imagem Docker
	@echo "$(GREEN)Construindo imagem Docker...$(NC)"
	@docker build \
		--build-arg BUILD_DATE=$(shell date -u +'%Y-%m-%dT%H:%M:%SZ') \
		--build-arg VCS_REF=$(shell git rev-parse --short HEAD 2>/dev/null || echo 'unknown') \
		--build-arg VERSION=$(VERSION) \
		-t $(DOCKER_IMAGE) .
	@echo "$(GREEN)✅ Imagem Docker construída: $(DOCKER_IMAGE)$(NC)"

docker-run: ## Executar container Docker
	@echo "$(GREEN)Executando container Docker...$(NC)"
	@docker run -d \
		--name $(DOCKER_CONTAINER) \
		-p 8080:8080 \
		-v $(PWD)/data:/app/data \
		-v $(PWD)/logs:/app/logs \
		-v $(PWD)/reports:/app/reports \
		-v $(PWD)/backups:/app/backups \
		$(DOCKER_IMAGE)
	@echo "$(GREEN)✅ Container iniciado: $(DOCKER_CONTAINER)$(NC)"
	@echo "$(BLUE)Acesse: http://localhost:8080$(NC)"

docker-stop: ## Parar container Docker
	@echo "$(YELLOW)Parando container Docker...$(NC)"
	@docker stop $(DOCKER_CONTAINER) 2>/dev/null || true
	@docker rm $(DOCKER_CONTAINER) 2>/dev/null || true
	@echo "$(GREEN)✅ Container parado$(NC)"

docker-logs: ## Ver logs do container
	@docker logs -f $(DOCKER_CONTAINER)

docker-shell: ## Acessar shell do container
	@docker exec -it $(DOCKER_CONTAINER) bash

docker: docker-build docker-run ## Construir e executar Docker

docker-compose-up: ## Iniciar com docker-compose
	@echo "$(GREEN)Iniciando com Docker Compose...$(NC)"
	@docker-compose up -d
	@echo "$(GREEN)✅ Serviços iniciados$(NC)"

docker-compose-down: ## Parar docker-compose
	@echo "$(YELLOW)Parando Docker Compose...$(NC)"
	@docker-compose down
	@echo "$(GREEN)✅ Serviços parados$(NC)"

docker-compose-logs: ## Ver logs do docker-compose
	@docker-compose logs -f

# ==============================================
# COMANDOS DE DESENVOLVIMENTO
# ==============================================

test: ## Executar testes
	@echo "$(GREEN)Executando testes...$(NC)"
	@if [ ! -d "$(VENV)" ]; then \
		echo "$(RED)❌ Ambiente virtual não encontrado. Execute 'make install' primeiro.$(NC)"; \
		exit 1; \
	fi
	@. $(VENV)/bin/activate && \
		$(PYTHON) -m pytest tests/ -v --cov=app --cov-report=html --cov-report=term

test-coverage: test ## Executar testes com relatório de cobertura
	@echo "$(BLUE)Relatório de cobertura gerado em: htmlcov/index.html$(NC)"

lint: ## Verificar código com linting
	@echo "$(GREEN)Verificando código...$(NC)"
	@. $(VENV)/bin/activate && \
		flake8 app.py run.py sophos_audit_integration.py --max-line-length=120 --ignore=E501,W503

format: ## Formatar código
	@echo "$(GREEN)Formatando código...$(NC)"
	@. $(VENV)/bin/activate && \
		black app.py run.py sophos_audit_integration.py --line-length=120

check: lint test ## Verificar código e executar testes

# ==============================================
# COMANDOS DE BANCO DE DADOS
# ==============================================

db-init: ## Inicializar banco de dados
	@echo "$(GREEN)Inicializando banco de dados...$(NC)"
	@. $(VENV)/bin/activate && $(PYTHON) -c "from app import init_database; init_database()"
	@echo "$(GREEN)✅ Banco de dados inicializado$(NC)"

db-reset: ## Resetar banco de dados
	@echo "$(YELLOW)Resetando banco de dados...$(NC)"
	@read -p "Tem certeza? Esta ação não pode ser desfeita [y/N]: " confirm && \
		if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
			rm -f data/databases/strati_audit.db; \
			$(MAKE) db-init; \
			echo "$(GREEN)✅ Banco de dados resetado$(NC)"; \
		else \
			echo "$(BLUE)Operação cancelada$(NC)"; \
		fi

db-backup: ## Fazer backup do banco
	@echo "$(GREEN)Fazendo backup do banco...$(NC)"
	@./scripts/backup.sh
	@echo "$(GREEN)✅ Backup concluído$(NC)"

# ==============================================
# COMANDOS DE BACKUP E RESTAURAÇÃO
# ==============================================

backup: ## Fazer backup completo do sistema
	@echo "$(GREEN)Fazendo backup do sistema...$(NC)"
	@./scripts/backup.sh
	@echo "$(GREEN)✅ Backup concluído$(NC)"

restore: ## Restaurar backup (especifique BACKUP_FILE=arquivo)
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "$(RED)❌ Especifique o arquivo de backup: make restore BACKUP_FILE=backup.tar.gz$(NC)"; \
		echo "$(BLUE)Backups disponíveis:$(NC)"; \
		ls -la backups/strati_backup_*.tar.gz 2>/dev/null || echo "Nenhum backup encontrado"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Restaurando backup: $(BACKUP_FILE)$(NC)"
	@./scripts/restore.sh $(BACKUP_FILE)

# ==============================================
# COMANDOS DE ATUALIZAÇÃO
# ==============================================

update: ## Atualizar sistema
	@echo "$(GREEN)Atualizando sistema...$(NC)"
	@./scripts/update.sh
	@echo "$(GREEN)✅ Sistema atualizado$(NC)"

update-deps: ## Atualizar dependências Python
	@echo "$(GREEN)Atualizando dependências...$(NC)"
	@. $(VENV)/bin/activate && \
		$(PIP) install --upgrade -r $(REQUIREMENTS)
	@echo "$(GREEN)✅ Dependências atualizadas$(NC)"

update-sophos: ## Atualizar Sophos Firewall Audit
	@echo "$(GREEN)Atualizando Sophos Firewall Audit...$(NC)"
	@if [ -d "sophos-firewall-audit" ]; then \
		cd sophos-firewall-audit && git pull; \
		echo "$(GREEN)✅ Sophos Firewall Audit atualizado$(NC)"; \
	else \
		echo "$(RED)❌ Diretório sophos-firewall-audit não encontrado$(NC)"; \
	fi

# ==============================================
# COMANDOS DE INSTALAÇÃO DO SISTEMA
# ==============================================

install-service: ## Instalar como serviço systemd
	@echo "$(GREEN)Instalando como serviço systemd...$(NC)"
	@sudo ./scripts/install_service.sh
	@echo "$(GREEN)✅ Serviço instalado$(NC)"
	@echo "$(BLUE)Use: sudo systemctl start strati-audit$(NC)"

uninstall-service: ## Remover serviço systemd
	@echo "$(YELLOW)Removendo serviço systemd...$(NC)"
	@sudo systemctl stop strati-audit 2>/dev/null || true
	@sudo systemctl disable strati-audit 2>/dev/null || true
	@sudo rm -f /etc/systemd/system/strati-audit.service
	@sudo systemctl daemon-reload
	@echo "$(GREEN)✅ Serviço removido$(NC)"

# ==============================================
# COMANDOS DE CONFIGURAÇÃO
# ==============================================

config: ## Editar arquivo de configuração
	@if [ -f "$(ENV_FILE)" ]; then \
		${EDITOR:-nano} $(ENV_FILE); \
	else \
		echo "$(RED)❌ Arquivo .env não encontrado. Execute 'make install' primeiro.$(NC)"; \
	fi

config-check: ## Verificar configuração
	@echo "$(GREEN)Verificando configuração...$(NC)"
	@. $(VENV)/bin/activate && $(PYTHON) run.py --check
	@echo "$(GREEN)✅ Configuração verificada$(NC)"

generate-secret: ## Gerar nova chave secreta
	@echo "$(GREEN)Nova chave secreta:$(NC)"
	@$(PYTHON) -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"
	@echo "$(YELLOW)Copie esta chave para seu arquivo .env$(NC)"

# ==============================================
# COMANDOS DE MONITORAMENTO
# ==============================================

logs: ## Ver logs do sistema
	@tail -f logs/strati_audit.log

logs-error: ## Ver logs de erro
	@tail -f logs/error.log

logs-access: ## Ver logs de acesso
	@tail -f logs/access.log

monitor: status ## Alias para status

health: ## Verificar saúde do sistema
	@echo "$(GREEN)Verificando saúde do sistema...$(NC)"
	@curl -s http://localhost:8080/api/health | python -m json.tool || echo "Sistema não está respondendo"

# ==============================================
# COMANDOS DE RELEASE
# ==============================================

version: ## Mostrar versão atual
	@echo "$(GREEN)Strati Audit System v$(VERSION)$(NC)"
	@echo "Python: $$($(PYTHON) --version)"
	@echo "Docker: $$(docker --version 2>/dev/null || echo 'Não instalado')"
	@echo "Git: $$(git --version 2>/dev/null || echo 'Não instalado')"

release: ## Preparar release
	@echo "$(GREEN)Preparando release v$(VERSION)...$(NC)"
	@git tag -a v$(VERSION) -m "Release version $(VERSION)"
	@echo "$(GREEN)✅ Tag v$(VERSION) criada$(NC)"
	@echo "$(BLUE)Execute 'git push origin v$(VERSION)' para publicar$(NC)"

# ==============================================
# COMANDOS DE DOCUMENTAÇÃO
# ==============================================

docs: ## Gerar documentação
	@echo "$(GREEN)Gerando documentação...$(NC)"
	@if [ -d "docs" ]; then \
		cd docs && make html; \
		echo "$(GREEN)✅ Documentação gerada em docs/_build/html/$(NC)"; \
	else \
		echo "$(YELLOW)Diretório docs não encontrado$(NC)"; \
	fi

readme: ## Mostrar README
	@if [ -f "README.md" ]; then \
		cat README.md; \
	else \
		echo "$(RED)README.md não encontrado$(NC)"; \
	fi

# ==============================================
# COMANDOS DE SEGURANÇA
# ==============================================

security-check: ## Verificar vulnerabilidades de segurança
	@echo "$(GREEN)Verificando vulnerabilidades...$(NC)"
	@. $(VENV)/bin/activate && \
		pip-audit || echo "$(YELLOW)pip-audit não instalado. Execute: pip install pip-audit$(NC)"

permissions: ## Corrigir permissões de arquivos
	@echo "$(GREEN)Corrigindo permissões...$(NC)"
	@chmod +x scripts/*.sh
	@chmod 750 data logs reports clients backups config
	@chmod 640 .env 2>/dev/null || true
	@echo "$(GREEN)✅ Permissões corrigidas$(NC)"

# ==============================================
# COMANDOS DE DESENVOLVIMENTO AVANÇADO
# ==============================================

shell: ## Abrir shell Python com contexto da aplicação
	@echo "$(GREEN)Abrindo shell Python...$(NC)"
	@. $(VENV)/bin/activate && $(PYTHON) -c "
from app import app, init_database
import sqlite3
import json
print('Strati Audit Shell - Contexto carregado')
print('Objetos disponíveis: app, init_database, sqlite3, json')
print('Para sair: exit()')
import code; code.interact(local=globals())
"

debug: ## Executar em modo debug avançado
	@echo "$(GREEN)Iniciando em modo debug avançado...$(NC)"
	@. $(VENV)/bin/activate && $(PYTHON) run.py --debug --log-level DEBUG

profile: ## Executar com profiling
	@echo "$(GREEN)Executando com profiling...$(NC)"
	@. $(VENV)/bin/activate && $(PYTHON) -m cProfile -o profile.stats run.py --dev

# ==============================================
# COMANDOS DE INFORMAÇÃO
# ==============================================

info: ## Mostrar informações do sistema
	@echo "$(GREEN)Informações do Sistema$(NC)"
	@echo "======================"
	@echo "Projeto: $(PROJECT_NAME)"
	@echo "Versão: $(VERSION)"
	@echo "Python: $$($(PYTHON) --version 2>&1)"
	@echo "Diretório: $$(pwd)"
	@echo "Usuário: $$(whoami)"
	@echo "Sistema: $$(uname -s)"
	@echo "Arquitetura: $$(uname -m)"
	@echo ""
	@echo "$(BLUE)Arquivos importantes:$(NC)"
	@ls -la app.py run.py $(ENV_FILE) $(REQUIREMENTS) 2>/dev/null || true
	@echo ""
	@echo "$(BLUE)Status dos serviços:$(NC)"
	@systemctl is-active strati-audit 2>/dev/null || echo "Serviço não instalado"

# ==============================================
# COMANDOS DE VALIDAÇÃO
# ==============================================

validate: ## Validar instalação completa
	@echo "$(GREEN)Validando instalação...$(NC)"
	@echo "$(BLUE)Verificando Python...$(NC)"
	@$(PYTHON) --version || (echo "$(RED)❌ Python não encontrado$(NC)" && exit 1)
	@echo "$(BLUE)Verificando ambiente virtual...$(NC)"
	@[ -d "$(VENV)" ] || (echo "$(RED)❌ Ambiente virtual não encontrado$(NC)" && exit 1)
	@echo "$(BLUE)Verificando arquivo .env...$(NC)"
	@[ -f "$(ENV_FILE)" ] || (echo "$(RED)❌ Arquivo .env não encontrado$(NC)" && exit 1)
	@echo "$(BLUE)Verificando banco de dados...$(NC)"
	@[ -f "data/databases/strati_audit.db" ] || (echo "$(RED)❌ Banco de dados não encontrado$(NC)" && exit 1)
	@echo "$(BLUE)Verificando Sophos Audit...$(NC)"
	@[ -f "sophos-firewall-audit/sophos_firewall_audit.py" ] || echo "$(YELLOW)⚠️  Sophos Audit não encontrado$(NC)"
	@echo "$(GREEN)✅ Validação concluída$(NC)"

# ==============================================
# VARIÁVEIS DE AMBIENTE PARA DESENVOLVIMENTO
# ==============================================

# Permitir override de variáveis
-include .env.local
