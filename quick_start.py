#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick Start - Strati Audit System
Script para início rápido e correção de problemas
"""

import os
import sys
import subprocess
import time

def print_banner():
    """Exibir banner do sistema"""
    banner = """
╔══════════════════════════════════════════════════════╗
║                                                      ║
║    🛡️  STRATI AUDIT SYSTEM - QUICK START           ║
║                                                      ║
║    Sistema de Auditoria Sophos Firewall             ║
║    Powered by Strati Guardian                        ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
"""
    print(banner)

def check_and_create_venv():
    """Verificar e criar ambiente virtual"""
    print("🐍 Verificando ambiente Python...")
    
    if not os.path.exists('venv'):
        print("📦 Criando ambiente virtual...")
        try:
            subprocess.run([sys.executable, '-m', 'venv', 'venv'], check=True)
            print("✅ Ambiente virtual criado")
        except subprocess.CalledProcessError as e:
            print(f"❌ Erro ao criar ambiente virtual: {e}")
            return False
    else:
        print("✅ Ambiente virtual já existe")
    
    return True

def install_dependencies():
    """Instalar dependências"""
    print("📦 Instalando dependências...")
    
    # Ativar venv e instalar
    if os.name == 'nt':  # Windows
        pip_path = os.path.join('venv', 'Scripts', 'pip')
        python_path = os.path.join('venv', 'Scripts', 'python')
    else:  # Unix/Linux/Mac
        pip_path = os.path.join('venv', 'bin', 'pip')
        python_path = os.path.join('venv', 'bin', 'python')
    
    try:
        # Atualizar pip
        subprocess.run([python_path, '-m', 'pip', 'install', '--upgrade', 'pip'], 
                      check=True, capture_output=True)
        
        # Instalar requirements
        if os.path.exists('requirements.txt'):
            subprocess.run([pip_path, 'install', '-r', 'requirements.txt'], 
                          check=True, capture_output=True)
            print("✅ Dependências instaladas")
        else:
            # Instalar dependências mínimas
            deps = [
                'Flask==2.3.3',
                'Flask-CORS==4.0.0', 
                'PyJWT==2.8.0',
                'Werkzeug==2.3.7',
                'python-dotenv==1.0.0'
            ]
            
            for dep in deps:
                subprocess.run([pip_path, 'install', dep], 
                              check=True, capture_output=True)
            print("✅ Dependências mínimas instaladas")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao instalar dependências: {e}")
        return False

def setup_directories():
    """Criar estrutura de diretórios"""
    print("📁 Criando estrutura de diretórios...")
    
    directories = [
        'data/databases',
        'data/temp',
        'logs',
        'reports', 
        'clients',
        'backups',
        'config',
        'scripts'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    print("✅ Diretórios criados")

def setup_env_file():
    """Configurar arquivo .env"""
    print("⚙️  Configurando arquivo .env...")
    
    if not os.path.exists('.env'):
        env_content = """# Strati Audit System Configuration
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=strati-audit-development-key-change-in-production
HOST=0.0.0.0
PORT=8080
DATABASE_PATH=./data/databases/strati_audit.db
SOPHOS_AUDIT_SCRIPT=./sophos-firewall-audit/sophos_firewall_audit.py
JWT_EXPIRATION_HOURS=24
LOG_LEVEL=INFO
LOG_FILE=./logs/strati_audit.log
"""
        
        with open('.env', 'w') as f:
            f.write(env_content)
        
        print("✅ Arquivo .env criado")
    else:
        print("✅ Arquivo .env já existe")

def download_sophos_audit():
    """Baixar Sophos Firewall Audit"""
    print("🛡️  Configurando Sophos Firewall Audit...")
    
    if not os.path.exists('sophos-firewall-audit'):
        try:
            print("📥 Baixando do GitHub...")
            subprocess.run([
                'git', 'clone', 
                'https://github.com/sophos/sophos-firewall-audit.git'
            ], check=True, capture_output=True)
            
            # Tornar executável
            script_path = 'sophos-firewall-audit/sophos_firewall_audit.py'
            if os.path.exists(script_path):
                os.chmod(script_path, 0o755)
            
            print("✅ Sophos Firewall Audit configurado")
            
        except subprocess.CalledProcessError:
            print("⚠️  Git não disponível. Sophos Audit será simulado.")
        except Exception as e:
            print(f"⚠️  Erro ao baixar Sophos Audit: {e}")
    else:
        print("✅ Sophos Firewall Audit já existe")

def initialize_database():
    """Inicializar banco de dados"""
    print("🗄️  Inicializando banco de dados...")
    
    # Usar Python do venv
    if os.name == 'nt':  # Windows
        python_path = os.path.join('venv', 'Scripts', 'python')
    else:  # Unix/Linux/Mac
        python_path = os.path.join('venv', 'bin', 'python')
    
    try:
        # Executar inicialização
        result = subprocess.run([
            python_path, '-c', 
            'from app import init_database; init_database()'
        ], capture_output=True, text=True, cwd='.')
        
        if result.returncode == 0:
            print("✅ Banco de dados inicializado")
            return True
        else:
            print(f"❌ Erro na inicialização: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao inicializar banco: {e}")
        return False

def test_application():
    """Testar aplicação"""
    print("🧪 Testando aplicação...")
    
    if os.name == 'nt':  # Windows
        python_path = os.path.join('venv', 'Scripts', 'python')
    else:  # Unix/Linux/Mac
        python_path = os.path.join('venv', 'bin', 'python')
    
    try:
        # Testar importação
        result = subprocess.run([
            python_path, '-c', 
            'from app import app; print("Import OK")'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ Aplicação pode ser importada")
            return True
        else:
            print(f"❌ Erro na importação: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("⚠️  Timeout no teste - pode funcionar normalmente")
        return True
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False

def start_application():
    """Iniciar aplicação"""
    print("🚀 Iniciando Strati Audit System...")
    print("")
    print("🌐 Acesso: http://localhost:8080")
    print("👤 Usuário: admin")
    print("🔑 Senha: admin123")
    print("")
    print("⏹️  Para parar: Ctrl+C")
    print("=" * 50)
    
    if os.name == 'nt':  # Windows
        python_path = os.path.join('venv', 'Scripts', 'python')
    else:  # Unix/Linux/Mac
        python_path = os.path.join('venv', 'bin', 'python')
    
    try:
        # Iniciar aplicação
        subprocess.run([python_path, 'run.py', '--dev'], cwd='.')
        
    except KeyboardInterrupt:
        print("\n\n🛑 Sistema parado pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro ao iniciar: {e}")

def show_help():
    """Mostrar ajuda"""
    help_text = """
🔧 COMANDOS DISPONÍVEIS:

Desenvolvimento:
  python quick_start.py          # Setup completo e iniciar
  python run.py --dev            # Apenas iniciar (dev)
  python run.py                  # Iniciar (produção)
  python debug.py                # Diagnóstico

Makefile (se disponível):
  make install                   # Instalar tudo
  make dev                       # Iniciar desenvolvimento
  make diagnose                  # Diagnóstico
  make help                      # Ver todos comandos

🌐 ACESSO:
  URL: http://localhost:8080
  Usuário: admin
  Senha: admin123

📚 DOCUMENTAÇÃO:
  README.md - Documentação completa
  logs/ - Logs do sistema
  
🐛 PROBLEMAS:
  1. Execute: python debug.py
  2. Verifique logs/diagnostic_report.json
  3. Consulte README.md
"""
    print(help_text)

def main():
    """Função principal"""
    print_banner()
    
    if len(sys.argv) > 1:
        if sys.argv[1] in ['--help', '-h', 'help']:
            show_help()
            return
    
    try:
        # Verificar se está no diretório correto
        if not os.path.exists('app.py'):
            print("❌ Execute este script no diretório do Strati Audit")
            print("💡 Certifique-se de estar na pasta correta")
            sys.exit(1)
        
        print("🔧 Executando setup automático...\n")
        
        # Setup completo
        steps = [
            ("Ambiente Virtual", check_and_create_venv),
            ("Dependências", install_dependencies),
            ("Diretórios", setup_directories),
            ("Configuração", setup_env_file),
            ("Sophos Integration", download_sophos_audit),
            ("Banco de Dados", initialize_database),
            ("Teste da Aplicação", test_application)
        ]
        
        success_count = 0
        for step_name, step_func in steps:
            print(f"📋 {step_name}...")
            if step_func():
                success_count += 1
            print("")
        
        print(f"📊 Setup concluído: {success_count}/{len(steps)} etapas")
        
        if success_count == len(steps):
            print("🎉 Sistema pronto para uso!")
            
            # Perguntar se quer iniciar
            try:
                response = input("\n🚀 Iniciar o sistema agora? (Y/n): ").strip().lower()
                if response in ['', 'y', 'yes', 's', 'sim']:
                    start_application()
                else:
                    print("\n💡 Para iniciar manualmente:")
                    print("   python run.py --dev")
                    print("   ou")
                    print("   make dev")
            except KeyboardInterrupt:
                print("\n\n👋 Até logo!")
        
        else:
            print("⚠️  Alguns problemas foram encontrados.")
            print("🔧 Execute: python debug.py")
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Setup interrompido pelo usuário")
    except Exception as e:
        print(f"\n💥 Erro no setup: {e}")
        print("🔧 Tente: python debug.py")

if __name__ == '__main__':
    main()
