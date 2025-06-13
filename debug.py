#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Diagnóstico - Strati Audit System
Este script verifica problemas comuns e corrige configurações
"""

import os
import sys
import sqlite3
import subprocess
from pathlib import Path

def check_python_version():
    """Verificar versão do Python"""
    print("🐍 Verificando Python...")
    if sys.version_info < (3, 8):
        print(f"❌ Python {sys.version} - Versão muito antiga (requer 3.8+)")
        return False
    else:
        print(f"✅ Python {sys.version} - OK")
        return True

def check_directories():
    """Verificar estrutura de diretórios"""
    print("\n📁 Verificando diretórios...")
    
    directories = [
        'data/databases',
        'logs',
        'reports', 
        'clients',
        'backups',
        'config',
        'scripts'
    ]
    
    all_ok = True
    for directory in directories:
        if os.path.exists(directory):
            print(f"✅ {directory} - Existe")
        else:
            print(f"❌ {directory} - Ausente")
            try:
                os.makedirs(directory, exist_ok=True)
                print(f"✅ {directory} - Criado")
            except Exception as e:
                print(f"❌ {directory} - Erro ao criar: {e}")
                all_ok = False
    
    return all_ok

def check_files():
    """Verificar arquivos essenciais"""
    print("\n📄 Verificando arquivos...")
    
    files = [
        'app.py',
        'run.py',
        'requirements.txt',
        'sophos_audit_integration.py'
    ]
    
    all_ok = True
    for file_path in files:
        if os.path.exists(file_path):
            print(f"✅ {file_path} - Existe")
        else:
            print(f"❌ {file_path} - Ausente")
            all_ok = False
    
    # Verificar .env
    if os.path.exists('.env'):
        print("✅ .env - Existe")
    else:
        print("⚠️  .env - Ausente")
        if os.path.exists('.env.example'):
            try:
                import shutil
                shutil.copy('.env.example', '.env')
                print("✅ .env - Criado a partir do exemplo")
            except Exception as e:
                print(f"❌ .env - Erro ao criar: {e}")
                all_ok = False
        else:
            print("❌ .env.example também ausente")
            all_ok = False
    
    return all_ok

def check_database():
    """Verificar banco de dados"""
    print("\n🗄️  Verificando banco de dados...")
    
    db_path = './data/databases/strati_audit.db'
    
    try:
        if not os.path.exists(db_path):
            print("❌ Banco de dados não existe")
            print("🔧 Tentando inicializar...")
            
            # Importar e inicializar
            sys.path.insert(0, '.')
            from app import init_database
            init_database()
            print("✅ Banco de dados inicializado")
        else:
            # Verificar integridade
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Verificar tabelas principais
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            required_tables = ['users', 'clients', 'firewalls', 'audits', 'audit_logs']
            missing_tables = [table for table in required_tables if table not in tables]
            
            if missing_tables:
                print(f"❌ Tabelas ausentes: {missing_tables}")
                print("🔧 Tentando recriar...")
                from app import init_database
                init_database()
                print("✅ Banco recriado")
            else:
                print("✅ Banco de dados OK")
            
            # Verificar usuários
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            print(f"👥 Usuários cadastrados: {user_count}")
            
            conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no banco: {e}")
        return False

def check_dependencies():
    """Verificar dependências Python"""
    print("\n📦 Verificando dependências...")
    
    try:
        import flask
        print(f"✅ Flask {flask.__version__}")
    except ImportError:
        print("❌ Flask não instalado")
        return False
    
    try:
        import flask_cors
        print("✅ Flask-CORS OK")
    except ImportError:
        print("❌ Flask-CORS não instalado")
        return False
    
    try:
        import jwt
        print("✅ PyJWT OK")
    except ImportError:
        print("❌ PyJWT não instalado")
        return False
    
    try:
        import werkzeug
        print(f"✅ Werkzeug {werkzeug.__version__}")
    except ImportError:
        print("❌ Werkzeug não instalado")
        return False
    
    return True

def check_sophos_integration():
    """Verificar integração Sophos"""
    print("\n🛡️  Verificando Sophos Firewall Audit...")
    
    sophos_dir = './sophos-firewall-audit'
    sophos_script = os.path.join(sophos_dir, 'sophos_firewall_audit.py')
    
    if os.path.exists(sophos_script):
        print("✅ Script Sophos encontrado")
        
        # Verificar se é executável
        if os.access(sophos_script, os.X_OK):
            print("✅ Script é executável")
        else:
            print("⚠️  Script não é executável, corrigindo...")
            try:
                os.chmod(sophos_script, 0o755)
                print("✅ Permissões corrigidas")
            except Exception as e:
                print(f"❌ Erro ao corrigir permissões: {e}")
    
    else:
        print("❌ Script Sophos não encontrado")
        print("🔧 Tentando baixar...")
        
        try:
            result = subprocess.run([
                'git', 'clone', 
                'https://github.com/sophos/sophos-firewall-audit.git'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Sophos Firewall Audit baixado")
                os.chmod(sophos_script, 0o755)
                print("✅ Permissões configuradas")
                return True
            else:
                print(f"❌ Erro ao baixar: {result.stderr}")
                return False
                
        except FileNotFoundError:
            print("❌ Git não encontrado. Instale git primeiro.")
            return False
        except Exception as e:
            print(f"❌ Erro: {e}")
            return False
    
    return True

def check_permissions():
    """Verificar permissões de arquivos"""
    print("\n🔐 Verificando permissões...")
    
    # Scripts devem ser executáveis
    scripts = [
        'scripts/start.sh',
        'scripts/stop.sh', 
        'scripts/monitor.sh',
        'scripts/backup.sh'
    ]
    
    for script in scripts:
        if os.path.exists(script):
            if os.access(script, os.X_OK):
                print(f"✅ {script} - Executável")
            else:
                print(f"⚠️  {script} - Corrigindo permissões...")
                try:
                    os.chmod(script, 0o755)
                    print(f"✅ {script} - Corrigido")
                except Exception as e:
                    print(f"❌ {script} - Erro: {e}")
        else:
            print(f"⚠️  {script} - Ausente")
    
    # Diretórios com permissões adequadas
    secure_dirs = ['data', 'logs', 'config', 'backups']
    for directory in secure_dirs:
        if os.path.exists(directory):
            try:
                os.chmod(directory, 0o750)
                print(f"✅ {directory} - Permissões seguras")
            except Exception as e:
                print(f"❌ {directory} - Erro: {e}")

def test_import():
    """Testar importação da aplicação"""
    print("\n🧪 Testando importação da aplicação...")
    
    try:
        sys.path.insert(0, '.')
        from app import app, init_database
        print("✅ Importação OK")
        
        # Testar criação da app
        with app.app_context():
