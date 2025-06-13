#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Strati Audit System - Script de Execução Principal
Arquivo: run.py

Este arquivo é o ponto de entrada principal para executar o Strati Audit System.
Pode ser usado tanto em desenvolvimento quanto em produção.

Autor: Strati Security Team
Data: 2025-13-06
Versão: 1.0.0
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# Adicionar o diretório atual ao Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import create_app, init_database
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Erro ao importar dependências: {e}")
    print("Execute: pip install -r requirements.txt")
    sys.exit(1)

def setup_logging(log_level='INFO', log_file=None):
    """
    Configurar sistema de logging
    
    Args:
        log_level (str): Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file (str): Caminho para arquivo de log (opcional)
    """
    # Converter string para nível de logging
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Nível de log inválido: {log_level}')
    
    # Configurar formato de log
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Configurar handlers
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        # Criar diretório de logs se não existir
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        # Adicionar handler para arquivo
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(log_format, date_format))
        handlers.append(file_handler)
    
    # Configurar logging básico
    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        datefmt=date_format,
        handlers=handlers,
        force=True
    )

def load_environment():
    """
    Carregar variáveis de ambiente
    """
    # Procurar arquivo .env
    env_file = Path('.env')
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✅ Arquivo .env carregado: {env_file.absolute()}")
    else:
        print("⚠️  Arquivo .env não encontrado. Usando variáveis de ambiente do sistema.")
    
    # Definir variáveis padrão se não estiverem definidas
    defaults = {
        'FLASK_ENV': 'production',
        'FLASK_DEBUG': 'False',
        'HOST': '0.0.0.0',
        'PORT': '8080',
        'LOG_LEVEL': 'INFO',
        'DATABASE_PATH': './data/databases/strati_audit.db',
        'SOPHOS_AUDIT_SCRIPT': './sophos-firewall-audit/sophos_firewall_audit.py'
    }
    
    for key, default_value in defaults.items():
        if key not in os.environ:
            os.environ[key] = default_value

def check_dependencies():
    """
    Verificar dependências e configurações necessárias
    """
    errors = []
    warnings = []
    
    # Verificar Python version
    if sys.version_info < (3, 8):
        errors.append(f"Python 3.8+ requerido. Versão atual: {sys.version}")
    
    # Verificar arquivos essenciais
    essential_files = [
        'app.py',
        'sophos_audit_integration.py'
    ]
    
    for file_path in essential_files:
        if not os.path.exists(file_path):
            errors.append(f"Arquivo essencial não encontrado: {file_path}")
    
    # Verificar diretórios
    essential_dirs = [
        'data/databases',
        'logs',
        'config'
    ]
    
    for dir_path in essential_dirs:
        if not os.path.exists(dir_path):
            warnings.append(f"Diretório não encontrado: {dir_path}")
            try:
                os.makedirs(dir_path, exist_ok=True)
                print(f"✅ Diretório criado: {dir_path}")
            except Exception as e:
                errors.append(f"Erro ao criar diretório {dir_path}: {e}")
    
    # Verificar script Sophos
    sophos_script = os.environ.get('SOPHOS_AUDIT_SCRIPT')
    if sophos_script and not os.path.exists(sophos_script):
        warnings.append(f"Script Sophos não encontrado: {sophos_script}")
        print("📥 Execute: git clone https://github.com/sophos/sophos-firewall-audit.git")
    
    # Mostrar avisos
    if warnings:
        print("\n⚠️  Avisos:")
        for warning in warnings:
            print(f"   - {warning}")
    
    # Verificar erros críticos
    if errors:
        print("\n❌ Erros críticos encontrados:")
        for error in errors:
            print(f"   - {error}")
        return False
    
    return True

def initialize_database():
    """
    Inicializar banco de dados se necessário
    """
    db_path = os.environ.get('DATABASE_PATH', './data/databases/strati_audit.db')
    
    try:
        if not os.path.exists(db_path):
            print("🗄️  Inicializando banco de dados...")
            init_database()
            print("✅ Banco de dados inicializado com sucesso")
        else:
            # Verificar integridade do banco
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            conn.close()
            
            if result[0] != 'ok':
                print("⚠️  Banco de dados pode estar corrompido. Reinicializando...")
                os.rename(db_path, f"{db_path}.backup")
                init_database()
                print("✅ Banco de dados reinicializado")
            else:
                print("✅ Banco de dados íntegro")
                
    except Exception as e:
        print(f"❌ Erro ao inicializar banco de dados: {e}")
        return False
    
    return True

def show_startup_info():
    """
    Mostrar informações de inicialização
    """
    host = os.environ.get('HOST', '0.0.0.0')
    port = os.environ.get('PORT', '8080')
    flask_env = os.environ.get('FLASK_ENV', 'production')
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    print("\n" + "="*60)
    print("🛡️  STRATI AUDIT SYSTEM")
    print("="*60)
    print(f"🌐 URL de Acesso: http://{host}:{port}")
    print(f"🏠 Host: {host}")
    print(f"🔌 Porta: {port}")
    print(f"🔧 Ambiente: {flask_env}")
    print(f"🐛 Debug: {'Ativado' if debug_mode else 'Desativado'}")
    print(f"📁 Diretório: {os.getcwd()}")
    print(f"🐍 Python: {sys.version.split()[0]}")
    print("-"*60)
    print("👤 Usuários padrão:")
    print("   • admin / admin123 (Administrator)")
    print("   • william / william123 (Administrator)")
    print("-"*60)
    print("🚀 Para parar o servidor: Ctrl+C")
    print("📚 Documentação: README.md")
    print("🔍 Logs: logs/strati_audit.log")
    print("="*60)

def run_development_server(app, host, port, debug=False):
    """
    Executar servidor de desenvolvimento Flask
    """
    try:
        app.run(
            host=host,
            port=int(port),
            debug=debug,
            threaded=True,
            use_reloader=False  # Evitar reload duplo
        )
    except KeyboardInterrupt:
        print("\n\n🛑 Servidor interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro ao executar servidor: {e}")
        sys.exit(1)

def run_production_server(app, host, port):
    """
    Executar servidor de produção com Gunicorn
    """
    try:
        import gunicorn.app.wsgiapp as wsgi
        
        # Configurar argumentos do Gunicorn
        sys.argv = [
            'gunicorn',
            '--bind', f'{host}:{port}',
            '--workers', '4',
            '--worker-class', 'sync',
            '--timeout', '300',
            '--keepalive', '2',
            '--max-requests', '1000',
            '--max-requests-jitter', '100',
            '--log-level', 'info',
            '--access-logfile', 'logs/access.log',
            '--error-logfile', 'logs/error.log',
            '--pid', 'strati_audit.pid',
            'app:app'
        ]
        
        # Executar Gunicorn
        wsgi.run()
        
    except ImportError:
        print("⚠️  Gunicorn não encontrado. Executando servidor de desenvolvimento...")
        print("   Para produção, instale: pip install gunicorn")
        run_development_server(app, host, port, debug=False)
    except KeyboardInterrupt:
        print("\n\n🛑 Servidor interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro ao executar servidor de produção: {e}")
        sys.exit(1)

def main():
    """
    Função principal
    """
    # Parser de argumentos de linha de comando
    parser = argparse.ArgumentParser(
        description='Strati Audit System - Sistema de Auditoria Sophos',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python run.py                          # Executar em modo produção
  python run.py --dev                    # Executar em modo desenvolvimento
  python run.py --host 127.0.0.1         # Especificar host
  python run.py --port 5000              # Especificar porta
  python run.py --debug                  # Ativar modo debug
  python run.py --log-level DEBUG        # Nível de log detalhado
        """
    )
    
    parser.add_argument(
        '--dev', '--development',
        action='store_true',
        help='Executar em modo desenvolvimento'
    )
    
    parser.add_argument(
        '--host',
        default=None,
        help='Host para bind do servidor (padrão: 0.0.0.0)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=None,
        help='Porta para bind do servidor (padrão: 8080)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Ativar modo debug'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default=None,
        help='Nível de logging'
    )
    
    parser.add_argument(
        '--log-file',
        default=None,
        help='Arquivo para salvar logs'
    )
    
    parser.add_argument(
        '--init-db',
        action='store_true',
        help='Apenas inicializar banco de dados e sair'
    )
    
    parser.add_argument(
        '--check',
        action='store_true',
        help='Apenas verificar dependências e configurações'
    )
    
    args = parser.parse_args()
    
    # Carregar variáveis de ambiente
    load_environment()
    
    # Configurar valores baseados em argumentos
    if args.host:
        os.environ['HOST'] = args.host
    if args.port:
        os.environ['PORT'] = str(args.port)
    if args.debug:
        os.environ['FLASK_DEBUG'] = 'True'
    if args.dev:
        os.environ['FLASK_ENV'] = 'development'
        os.environ['FLASK_DEBUG'] = 'True'
    
    # Configurar logging
    log_level = args.log_level or os.environ.get('LOG_LEVEL', 'INFO')
    log_file = args.log_file or os.environ.get('LOG_FILE', 'logs/strati_audit.log')
    
    setup_logging(log_level, log_file)
    logger = logging.getLogger(__name__)
    
    logger.info("Iniciando Strati Audit System...")
    
    # Verificar dependências
    if not check_dependencies():
        print("\n❌ Falha na verificação de dependências")
        sys.exit(1)
    
    # Apenas verificar se solicitado
    if args.check:
        print("\n✅ Todas as verificações passaram")
        sys.exit(0)
    
    # Inicializar banco de dados
    if not initialize_database():
        print("\n❌ Falha na inicialização do banco de dados")
        sys.exit(1)
    
    # Apenas inicializar DB se solicitado
    if args.init_db:
        print("\n✅ Banco de dados inicializado com sucesso")
        sys.exit(0)
    
    # Criar aplicação Flask
    try:
        app = create_app()
        logger.info("Aplicação Flask criada com sucesso")
    except Exception as e:
        logger.error(f"Erro ao criar aplicação Flask: {e}")
        print(f"\n❌ Erro ao criar aplicação: {e}")
        sys.exit(1)
    
    # Obter configurações de rede
    host = os.environ.get('HOST', '0.0.0.0')
    port = os.environ.get('PORT', '8080')
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    flask_env = os.environ.get('FLASK_ENV', 'production')
    
    # Mostrar informações de inicialização
    show_startup_info()
    
    # Executar servidor
    try:
        if flask_env == 'development' or debug_mode:
            logger.info("Executando servidor de desenvolvimento")
            run_development_server(app, host, port, debug_mode)
        else:
            logger.info("Executando servidor de produção")
            run_production_server(app, host, port)
            
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
        print(f"\n💥 Erro fatal: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
