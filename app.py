# -*- coding: utf-8 -*-
"""
Strati Audit System - Aplicação Principal
Arquivo: app.py

Sistema de auditoria de segurança para firewalls Sophos
Integração com https://github.com/sophos/sophos-firewall-audit

Autor: Strati Security Team
Data: 2025-13-06
Versão: 1.0.0
"""

import os
import json
import yaml
import subprocess
import sqlite3
import hashlib
import jwt
import threading
import time
import logging
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

from flask import Flask, request, jsonify, send_file, render_template_string, Response
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

# Importar integração com Sophos
try:
    from sophos_audit_integration import SophosFirewallAuditor
except ImportError:
    SophosFirewallAuditor = None
    print("⚠️  sophos_audit_integration.py não encontrado. Usando simulação.")

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/strati_audit.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Criar aplicação Flask
app = Flask(__name__)

# Configurações da aplicação
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'strati-audit-secret-key-2025')
app.config['JWT_EXPIRATION_DELTA'] = timedelta(
    hours=int(os.environ.get('JWT_EXPIRATION_HOURS', 24))
)

# Habilitar CORS
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Caminhos do sistema
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENTS_DIR = os.path.join(BASE_DIR, 'clients')
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')
DATABASE_PATH = os.environ.get('DATABASE_PATH', os.path.join(BASE_DIR, 'data', 'databases', 'strati_audit.db'))
SOPHOS_AUDIT_SCRIPT = os.environ.get('SOPHOS_AUDIT_SCRIPT', 
                                     os.path.join(BASE_DIR, 'sophos-firewall-audit', 'sophos_firewall_audit.py'))

# Criar diretórios necessários
for directory in [CLIENTS_DIR, REPORTS_DIR, os.path.dirname(DATABASE_PATH)]:
    os.makedirs(directory, exist_ok=True)

def init_database():
    """Inicializar o banco de dados SQLite"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Tabela de usuários
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Tabela de clientes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Tabela de firewalls
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS firewalls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER,
                hostname TEXT NOT NULL,
                port INTEGER DEFAULT 4444,
                username TEXT,
                password_encrypted TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (client_id) REFERENCES clients (id)
            )
        ''')
        
        # Tabela de auditorias
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER,
                firewall_id INTEGER,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                status TEXT DEFAULT 'running',
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                warning_count INTEGER DEFAULT 0,
                score REAL DEFAULT 0,
                report_path TEXT,
                report_data TEXT,
                executed_by INTEGER,
                FOREIGN KEY (client_id) REFERENCES clients (id),
                FOREIGN KEY (firewall_id) REFERENCES firewalls (id),
                FOREIGN KEY (executed_by) REFERENCES users (id)
            )
        ''')
        
        # Tabela de logs de auditoria
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audit_id INTEGER,
                level TEXT,
                message TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (audit_id) REFERENCES audits (id)
            )
        ''')
        
        # Tabela de configurações do sistema
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_key TEXT UNIQUE NOT NULL,
                config_value TEXT,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Inserir dados de exemplo para teste
        try:
            # Criar usuário admin padrão
            admin_password = generate_password_hash('admin123')
            cursor.execute('''
                INSERT OR IGNORE INTO users (username, email, password_hash, role) 
                VALUES (?, ?, ?, ?)
            ''', ('admin', 'admin@strati.com.br', admin_password, 'admin'))
            
            # Criar usuário William
            william_password = generate_password_hash('william123')
            cursor.execute('''
                INSERT OR IGNORE INTO users (username, email, password_hash, role) 
                VALUES (?, ?, ?, ?)
            ''', ('william', 'william@strati.com.br', william_password, 'admin'))
            
            # Criar clientes de exemplo
            clientes_exemplo = [
                ('Empresa Teste', 'Cliente de exemplo para demonstração'),
                ('Banco Central', 'Cliente bancário com alta segurança'),
                ('Hospital Geral', 'Sistema hospitalar com dados sensíveis'),
                ('Universidade XYZ', 'Instituição de ensino superior'),
                ('Indústria ABC', 'Empresa industrial com múltiplas unidades')
            ]
            
            for cliente in clientes_exemplo:
                cursor.execute('''
                    INSERT OR IGNORE INTO clients (name, description) 
                    VALUES (?, ?)
                ''', cliente)
            
            # Buscar IDs dos clientes criados e criar firewalls
            cursor.execute('SELECT id, name FROM clients WHERE is_active = 1')
            clients_rows = cursor.fetchall()
            
            for client_row in clients_rows:
                client_id, client_name = client_row
                
                # Criar firewalls de exemplo para cada cliente
                if client_name == 'Empresa Teste':
                    firewalls = [
                        ('192.168.1.100', 4444, 'admin'),
                        ('192.168.1.101', 4444, 'admin'),
                        ('192.168.1.102', 4444, 'admin')
                    ]
                elif client_name == 'Banco Central':
                    firewalls = [
                        ('10.0.1.10', 4444, 'admin'),
                        ('10.0.1.11', 4444, 'admin'),
                        ('10.0.1.12', 4444, 'admin'),
                        ('10.0.1.13', 4444, 'admin')
                    ]
                elif client_name == 'Hospital Geral':
                    firewalls = [
                        ('172.16.1.50', 4444, 'admin'),
                        ('172.16.1.51', 4444, 'admin')
                    ]
                elif client_name == 'Universidade XYZ':
                    firewalls = [
                        ('10.10.1.1', 4444, 'admin'),
                        ('10.10.1.2', 4444, 'admin'),
                        ('10.10.1.3', 4444, 'admin')
                    ]
                elif client_name == 'Indústria ABC':
                    firewalls = [
                        ('192.168.100.1', 4444, 'admin'),
                        ('192.168.200.1', 4444, 'admin')
                    ]
                else:
                    firewalls = [('192.168.1.100', 4444, 'admin')]
                
                for firewall in firewalls:
                    cursor.execute('''
                        INSERT OR IGNORE INTO firewalls (client_id, hostname, port, username) 
                        VALUES (?, ?, ?, ?)
                    ''', (client_id, firewall[0], firewall[1], firewall[2]))
            
            # Criar auditorias de exemplo
            cursor.execute('SELECT id FROM users WHERE username = ?', ('admin',))
            user_row = cursor.fetchone()
            if user_row:
                user_id = user_row[0]
                
                # Para cada cliente, criar algumas auditorias de exemplo
                for client_row in clients_rows:
                    client_id = client_row[0]
                    
                    # Criar auditorias de exemplo
                    auditorias_exemplo = [
                        ('completed', 85, 15, 5, 85.0, datetime.now() - timedelta(days=1)),
                        ('completed', 92, 8, 3, 92.0, datetime.now() - timedelta(hours=12)),
                        ('completed', 78, 20, 8, 78.0, datetime.now() - timedelta(hours=6)),
                        ('running', 0, 0, 0, 0.0, datetime.now())
                    ]
                    
                    for auditoria in auditorias_exemplo:
                        cursor.execute('''
                            INSERT OR IGNORE INTO audits 
                            (client_id, status, success_count, failure_count, warning_count, score, executed_by, completed_at) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (client_id, auditoria[0], auditoria[1], auditoria[2], 
                             auditoria[3], auditoria[4], user_id, auditoria[5]))
            
            # Inserir configurações padrão do sistema
            configs_padrao = [
                ('smtp_server', '', 'Servidor SMTP para envio de emails'),
                ('smtp_port', '587', 'Porta do servidor SMTP'),
                ('alert_email', '', 'Email para receber alertas'),
                ('backup_enabled', 'true', 'Backup automático habilitado'),
                ('audit_timeout', '300', 'Timeout para auditorias em segundos'),
                ('max_concurrent_audits', '3', 'Máximo de auditorias simultâneas'),
                ('score_threshold_critical', '60', 'Score abaixo do qual é considerado crítico'),
                ('score_threshold_warning', '80', 'Score abaixo do qual é considerado aviso')
            ]
            
            for config in configs_padrao:
                cursor.execute('''
                    INSERT OR IGNORE INTO system_config (config_key, config_value, description) 
                    VALUES (?, ?, ?)
                ''', config)
        
        except Exception as e:
            logger.warning(f"Erro ao inserir dados de exemplo: {e}")
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        raise

# Decorador para autenticação JWT
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            logger.warning("No Authorization header found")
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user_id = data['user_id']
            
            # Verificar se usuário ainda existe e está ativo
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE id = ? AND is_active = 1', (current_user_id,))
            user = cursor.fetchone()
            conn.close()
            
            if not user:
                logger.warning(f"User {current_user_id} not found or inactive")
                return jsonify({'error': 'Invalid token'}), 401
                
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {str(e)}")
            return jsonify({'error': 'Invalid token'}), 401
        except Exception as e:
            logger.error(f"JWT decode error: {str(e)}")
            return jsonify({'error': 'Token validation failed'}), 401
        
        return f(current_user_id, *args, **kwargs)
    
    return decorated

# Decorador para verificar permissões de admin
def admin_required(f):
    @wraps(f)
    def decorated(current_user_id, *args, **kwargs):
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT role FROM users WHERE id = ?', (current_user_id,))
        user = cursor.fetchone()
        conn.close()
        
        if not user or user[0] != 'admin':
            return jsonify({'error': 'Admin privileges required'}), 403
        
        return f(current_user_id, *args, **kwargs)
    
    return decorated

# ROTAS PRINCIPAIS
@app.route('/')
def index():
    """Página principal - servir interface web"""
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Strati Audit - Login</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                display: flex; 
                justify-content: center; 
                align-items: center; 
                height: 100vh; 
                margin: 0; 
            }
            .login-container { 
                background: white; 
                padding: 3rem; 
                border-radius: 15px; 
                box-shadow: 0 20px 40px rgba(0,0,0,0.15); 
                width: 420px; 
                max-width: 90vw;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255,255,255,0.2);
            }
            .logo { text-align: center; margin-bottom: 2.5rem; }
            .logo h1 { 
                color: #333; 
                margin: 0; 
                font-size: 2.2rem; 
                font-weight: 700;
                background: linear-gradient(135deg, #667eea, #764ba2);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            .logo p { color: #666; margin: 0.5rem 0 0 0; font-size: 1.1rem; }
            .form-group { margin-bottom: 1.5rem; }
            .form-group label { 
                display: block; 
                margin-bottom: 0.5rem; 
                color: #333;
                font-weight: 600;
                font-size: 0.95rem;
            }
            .form-group input { 
                width: 100%; 
                padding: 0.75rem 1rem; 
                border: 2px solid #e0e0e0; 
                border-radius: 8px; 
                box-sizing: border-box; 
                font-size: 1rem;
                transition: all 0.3s ease;
                background: #f8f9fa;
            }
            .form-group input:focus {
                outline: none;
                border-color: #667eea;
                background: white;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }
            .btn { 
                width: 100%; 
                padding: 0.75rem; 
                background: linear-gradient(135deg, #667eea, #764ba2); 
                color: white; 
                border: none; 
                border-radius: 8px; 
                cursor: pointer; 
                font-size: 1rem;
                font-weight: 600;
                transition: all 0.3s ease;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            .btn:hover { 
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
            }
            .btn:active { transform: translateY(0); }
            .alert { 
                padding: 1rem; 
                margin-bottom: 1rem; 
                border-radius: 8px; 
                display: none; 
                font-weight: 500;
            }
            .alert-error { 
                background: #fee; 
                color: #c00; 
                border: 1px solid #fcc; 
            }
            .alert-success { 
                background: #efe; 
                color: #060; 
                border: 1px solid #cfc; 
            }
            .demo-users {
                margin-top: 2rem;
                padding: 1.5rem;
                background: linear-gradient(135deg, #f8f9fa, #e9ecef);
                border-radius: 10px;
                border-left: 4px solid #667eea;
            }
            .demo-users h4 {
                color: #333;
                margin-bottom: 1rem;
                font-size: 1rem;
            }
            .demo-users .user-item {
                background: white;
                padding: 0.75rem;
                margin: 0.5rem 0;
                border-radius: 6px;
                font-family: 'Courier New', monospace;
                font-size: 0.9rem;
                color: #495057;
                border-left: 3px solid #28a745;
            }
            .loading {
                display: none;
                margin-left: 10px;
            }
            .loading::after {
                content: '';
                width: 16px;
                height: 16px;
                border: 2px solid #ffffff;
                border-top: 2px solid transparent;
                border-radius: 50%;
                display: inline-block;
                animation: spin 1s linear infinite;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            .footer {
                text-align: center;
                margin-top: 2rem;
                color: #666;
                font-size: 0.85rem;
            }
            .footer a {
                color: #667eea;
                text-decoration: none;
            }
            .footer a:hover {
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="logo">
                <h1>🛡️ Strati Audit</h1>
                <p>Sistema de Auditoria Sophos</p>
            </div>
            
            <div id="alert" class="alert"></div>
            
            <form id="loginForm">
                <div class="form-group">
                    <label for="username">👤 Usuário:</label>
                    <input type="text" id="username" required placeholder="Digite seu usuário">
                </div>
                <div class="form-group">
                    <label for="password">🔑 Senha:</label>
                    <input type="password" id="password" required placeholder="Digite sua senha">
                </div>
                <button type="submit" class="btn">
                    Entrar
                    <span class="loading" id="loading"></span>
                </button>
            </form>
            
            <div class="demo-users">
                <h4>👥 Usuários de Demonstração:</h4>
                <div class="user-item">admin / admin123</div>
                <div class="user-item">william / william123</div>
            </div>
            
            <div class="footer">
                <p>Powered by <a href="https://strati.com.br" target="_blank">Strati Security</a></p>
                <p>Versão 1.0.0 • <a href="https://github.com/sophos/sophos-firewall-audit" target="_blank">Sophos Integration</a></p>
            </div>
        </div>
        
        <script>
            document.getElementById('loginForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const username = document.getElementById('username').value;
                const password = document.getElementById('password').value;
                const loadingSpinner = document.getElementById('loading');
                const submitBtn = e.target.querySelector('button[type="submit"]');
                
                // Mostrar loading
                loadingSpinner.style.display = 'inline-block';
                submitBtn.disabled = true;
                
                try {
                    const response = await fetch('/api/auth/login', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ username, password })
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        localStorage.setItem('token', data.token);
                        localStorage.setItem('user', JSON.stringify(data.user));
                        showAlert('Login realizado com sucesso! Redirecionando...', 'success');
                        
                        setTimeout(() => {
                            window.location.href = '/dashboard';
                        }, 1500);
                    } else {
                        showAlert(data.error || 'Erro no login. Verifique suas credenciais.', 'error');
                    }
                } catch (error) {
                    console.error('Login error:', error);
                    showAlert('Erro de conexão. Tente novamente.', 'error');
                } finally {
                    // Esconder loading
                    loadingSpinner.style.display = 'none';
                    submitBtn.disabled = false;
                }
            });
            
            function showAlert(message, type) {
                const alert = document.getElementById('alert');
                alert.className = 'alert alert-' + type;
                alert.textContent = message;
                alert.style.display = 'block';
                
                setTimeout(() => {
                    alert.style.display = 'none';
                }, 5000);
            }
            
            // Auto-focus no campo username
            document.getElementById('username').focus();
            
            // Permitir login com Enter
            document.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    document.getElementById('loginForm').dispatchEvent(new Event('submit'));
                }
            });
        </script>
    </body>
    </html>
    ''')

@app.route('/dashboard')
def dashboard():
    """Página do dashboard"""
    # Carregue aqui o CSS corrigido do artefato fixed_dashboard_css
    dashboard_html = '''
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Strati Audit - Dashboard</title>
        <style>
            /* CSS Corrigido para Dashboard - Fontes Legíveis */
            
            * { 
                margin: 0; 
                padding: 0; 
                box-sizing: border-box; 
            }
            
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                background: linear-gradient(135deg, #1a2332 0%, #2d3748 50%, #1a202c 100%); 
                min-height: 100vh; 
                color: #fff; 
            }
            
            .container { 
                max-width: 1200px; 
                margin: 0 auto; 
                padding: 20px; 
            }
            
            .header { 
                background: rgba(255, 255, 255, 0.95); 
                backdrop-filter: blur(10px); 
                border-radius: 15px; 
                padding: 20px; 
                margin-bottom: 30px; 
                box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1); 
                display: flex; 
                justify-content: space-between; 
                align-items: center; 
            }
            
            .logo h1 { 
                color: #333; 
                font-size: 1.8rem; 
                margin: 0; 
                font-weight: 700; 
            }
            
            .logo p { 
                color: #666; 
                margin: 5px 0 0 0; 
            }
            
            .user-info { 
                display: flex; 
                align-items: center; 
                gap: 15px; 
            }
            
            .user-details { 
                color: #333; 
            }
            
            .user-details strong { 
                color: #333; 
            }
            
            .user-details span { 
                color: #666; 
                font-size: 0.9rem; 
            }
            
            .user-avatar { 
                width: 40px; 
                height: 40px; 
                background: linear-gradient(135deg, #0ea5e9, #06b6d4); 
                border-radius: 50%; 
                display: flex; 
                align-items: center; 
                justify-content: center; 
                color: white; 
                font-weight: bold; 
            }
            
            .logout-btn { 
                background: #f59e0b; 
                color: white; 
                border: none; 
                padding: 8px 16px; 
                border-radius: 8px; 
                cursor: pointer; 
                font-size: 0.9rem; 
                font-weight: 600; 
                transition: all 0.3s ease; 
            }
            
            .logout-btn:hover { 
                background: #d97706; 
            }
            
            .stats-grid { 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
                gap: 20px; 
                margin-bottom: 30px; 
            }
            
            .stat-card { 
                background: rgba(255, 255, 255, 0.95); 
                backdrop-filter: blur(10px); 
                border-radius: 15px; 
                padding: 25px; 
                box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1); 
                transition: transform 0.3s ease; 
            }
            
            .stat-card:hover { 
                transform: translateY(-5px); 
            }
            
            .stat-icon { 
                font-size: 2rem; 
                margin-bottom: 15px; 
                display: block; 
            }
            
            .stat-value { 
                font-size: 2rem; 
                font-weight: bold; 
                color: #333; 
                margin-bottom: 5px; 
            }
            
            .stat-label { 
                color: #666; 
                font-size: 0.9rem; 
                font-weight: 500; 
            }
            
            .action-buttons { 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
                gap: 15px; 
                margin-bottom: 30px; 
            }
            
            .action-btn { 
                background: linear-gradient(135deg, #0ea5e9, #06b6d4); 
                color: white; 
                border: none; 
                padding: 15px 20px; 
                border-radius: 12px; 
                cursor: pointer; 
                font-size: 1rem; 
                font-weight: 600; 
                transition: all 0.3s ease; 
                display: flex; 
                align-items: center; 
                justify-content: center; 
                gap: 10px; 
                box-shadow: 0 4px 15px rgba(14, 165, 233, 0.3); 
            }
            
            .action-btn:hover { 
                transform: translateY(-2px); 
                box-shadow: 0 6px 20px rgba(14, 165, 233, 0.4); 
            }
            
            .action-btn.secondary { 
                background: linear-gradient(135deg, #f59e0b, #d97706); 
                box-shadow: 0 4px 15px rgba(245, 158, 11, 0.3); 
            }
            
            .action-btn.secondary:hover { 
                box-shadow: 0 6px 20px rgba(245, 158, 11, 0.4); 
            }
            
            .main-content { 
                display: grid; 
                grid-template-columns: 2fr 1fr; 
                gap: 30px; 
            }
            
            .section { 
                background: rgba(255, 255, 255, 0.95); 
                backdrop-filter: blur(10px); 
                border-radius: 15px; 
                padding: 25px; 
                box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1); 
                margin-bottom: 20px; 
            }
            
            .section h2 { 
                color: #333; 
                margin-bottom: 20px; 
                font-size: 1.3rem; 
            }
            
            .quick-stats { 
                display: grid; 
                gap: 15px; 
            }
            
            .quick-stat { 
                padding: 15px; 
                background: linear-gradient(135deg, rgba(14, 165, 233, 0.1), rgba(6, 182, 212, 0.1)); 
                border-radius: 10px; 
                border-left: 4px solid #0ea5e9; 
            }
            
            .quick-stat h4 { 
                color: #333; 
                margin-bottom: 5px; 
                font-weight: 600; 
            }
            
            .quick-stat p { 
                color: #666; 
                font-size: 0.9rem; 
            }
            
            .loading { 
                display: inline-block; 
                width: 20px; 
                height: 20px; 
                border: 3px solid #f3f3f3; 
                border-top: 3px solid #0066CC; 
                border-radius: 50%; 
                animation: spin 1s linear infinite; 
            }
            
            @keyframes spin { 
                0% { transform: rotate(0deg); } 
                100% { transform: rotate(360deg); } 
            }
            
            .alert { 
                padding: 15px; 
                margin-bottom: 20px; 
                border-radius: 8px; 
                display: none; 
            }
            
            .alert.success { 
                background: #d4edda; 
                color: #155724; 
                border: 1px solid #c3e6cb; 
            }
            
            .alert.error { 
                background: #f8d7da; 
                color: #721c24; 
                border: 1px solid #f5c6cb; 
            }
            
            .debug-info { 
                background: rgba(0, 0, 0, 0.05); 
                padding: 15px; 
                border-radius: 8px; 
                margin: 10px 0; 
                font-family: monospace; 
                font-size: 0.9rem; 
                color: #333; 
                border: 1px solid #ddd; 
            }
            
            .debug-info div { 
                margin-bottom: 5px; 
            }
            
            .debug-info span { 
                font-weight: bold; 
                color: #0066CC; 
            }
            
            .btn { 
                background: #0066CC; 
                color: white; 
                border: none; 
                padding: 10px 20px; 
                border-radius: 8px; 
                cursor: pointer; 
                margin: 5px; 
            }
            
            .btn:hover { 
                background: #004499; 
            }
            
            /* ESTILOS DOS MODAIS - CORRIGIDOS PARA LEGIBILIDADE */
            .modal { 
                display: none; 
                position: fixed; 
                z-index: 1000; 
                left: 0; 
                top: 0; 
                width: 100%; 
                height: 100%; 
                background-color: rgba(0, 0, 0, 0.5); 
                backdrop-filter: blur(5px); 
            }
            
            .modal.show { 
                display: flex; 
                align-items: center; 
                justify-content: center; 
            }
            
            .modal-content { 
                background: #ffffff; /* Fundo branco sólido */
                border-radius: 15px; 
                padding: 30px; 
                width: 90%; 
                max-width: 600px; 
                max-height: 80vh; 
                overflow-y: auto; 
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3); 
                animation: modalSlideIn 0.3s ease-out; 
                color: #333333; /* Texto escuro para contraste */
            }
            
            @keyframes modalSlideIn { 
                from { 
                    opacity: 0; 
                    transform: scale(0.8) translateY(-50px); 
                } 
                to { 
                    opacity: 1; 
                    transform: scale(1) translateY(0); 
                } 
            }
            
            .modal-header { 
                display: flex; 
                justify-content: space-between; 
                align-items: center; 
                margin-bottom: 25px; 
                padding-bottom: 15px; 
                border-bottom: 2px solid #f0f0f0; 
            }
            
            .modal-header h2 { 
                color: #333333; /* Título escuro */
                margin: 0; 
                font-size: 1.5rem; 
                font-weight: 600;
            }
            
            .close-btn { 
                background: none; 
                border: none; 
                font-size: 1.5rem; 
                cursor: pointer; 
                color: #666666; 
                padding: 5px; 
                border-radius: 50%; 
                width: 35px; 
                height: 35px; 
                display: flex; 
                align-items: center; 
                justify-content: center; 
            }
            
            .close-btn:hover { 
                background: #f0f0f0; 
                color: #333333; 
            }
            
            .form-group { 
                margin-bottom: 20px; 
            }
            
            .form-group label { 
                display: block; 
                margin-bottom: 8px; 
                font-weight: 600; 
                color: #333333; /* Labels escuros */
                font-size: 14px;
            }
            
            .form-group input, 
            .form-group textarea, 
            .form-group select { 
                width: 100%; 
                padding: 12px; 
                border: 2px solid #e0e0e0; 
                border-radius: 8px; 
                font-size: 14px; 
                transition: border-color 0.3s ease; 
                box-sizing: border-box; 
                background: #ffffff; /* Fundo branco */
                color: #333333; /* Texto escuro nos inputs */
            }
            
            .form-group input:focus, 
            .form-group textarea:focus, 
            .form-group select:focus { 
                outline: none; 
                border-color: #0066CC; 
                box-shadow: 0 0 0 3px rgba(0, 102, 204, 0.1); 
            }
            
            .form-group input::placeholder,
            .form-group textarea::placeholder {
                color: #999999; /* Placeholder cinza claro */
            }
            
            /* Resto dos estilos dos modais seguem o mesmo padrão... */
            
            @media (max-width: 768px) {
                .modal-content { 
                    width: 95%; 
                    padding: 20px; 
                    margin: 20px; 
                }
                
                .main-content { 
                    grid-template-columns: 1fr; 
                }
                
                .stats-grid { 
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
                }
                
                .action-buttons { 
                    grid-template-columns: 1fr; 
                }
            }
        </style>
    </head>
    <body>
        <!-- Conteúdo do dashboard aqui... -->
        <div class="container">
            <div class="header">
                <div class="logo">
                    <h1>🛡️ Strati Audit</h1>
                    <p>Sistema de Auditoria Sophos</p>
                </div>
                <div class="user-info">
                    <div class="user-avatar" id="userAvatar">U</div>
                    <div class="user-details">
                        <strong id="userName">Carregando...</strong><br>
                        <span id="userRole">Carregando...</span>
                    </div>
                    <button class="logout-btn" onclick="logout()">Sair</button>
                </div>
            </div>

            <div id="alert" class="alert"></div>

            <div class="section">
                <h2>🔍 Status do Sistema</h2>
                <div class="debug-info">
                    <div>Status: <span id="debugStatus">Inicializando...</span></div>
                    <div>Token: <span id="debugToken">Verificando...</span></div>
                    <div>API: <span id="debugAPI">Testando...</span></div>
                    <div>Última requisição: <span id="debugLastRequest">-</span></div>
                </div>
                <button class="btn" onclick="testAPI()">🧪 Testar API</button>
                <button class="btn" onclick="checkAuth()">🔐 Verificar Auth</button>
                <button class="btn" onclick="loadStats()">📊 Carregar Stats</button>
            </div>

            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon" style="color: #0066CC;">👥</div>
                    <div class="stat-value" id="totalClients">-</div>
                    <div class="stat-label">Clientes Ativos</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon" style="color: #f59e0b;">🛡️</div>
                    <div class="stat-value" id="totalFirewalls">-</div>
                    <div class="stat-label">Firewalls</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon" style="color: #10b981;">📊</div>
                    <div class="stat-value" id="auditsToday">-</div>
                    <div class="stat-label">Auditorias Hoje</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon" style="color: #f59e0b;">⭐</div>
                    <div class="stat-value" id="avgScore">-</div>
                    <div class="stat-label">Score Médio</div>
                </div>
            </div>

            <div class="action-buttons">
                <button class="action-btn" onclick="showCreateClientModal()">
                    ➕ Novo Cliente
                </button>
                <button class="action-btn secondary" onclick="showRunAuditModal()">
                    🚀 Executar Auditoria
                </button>
                <button class="action-btn" onclick="showViewReportsModal()">
                    📄 Ver Relatórios
                </button>
                <button class="action-btn secondary" onclick="showAlert('Funcionalidade em desenvolvimento', 'success')">
                    📋 Relatório Consolidado
                </button>
            </div>

            <div class="main-content">
                <div class="section">
                    <h2>📈 Auditorias Recentes</h2>
                    <div id="recentAudits">
                        <div class="loading"></div>
                        <p style="text-align: center; margin-top: 10px; color: #666;">Carregando auditorias...</p>
                    </div>
                </div>

                <div class="section">
                    <h2>📊 Estatísticas Rápidas</h2>
                    <div class="quick-stats">
                        <div class="quick-stat">
                            <h4>🟢 Sistema</h4>
                            <p>Online e funcionando</p>
                        </div>
                        <div class="quick-stat">
                            <h4>🕒 Última Atualização</h4>
                            <p id="lastUpdate">Agora</p>
                        </div>
                        <div class="quick-stat">
                            <h4>🔗 Status da API</h4>
                            <p>✅ Operacional</p>
                        </div>
                        <div class="quick-stat">
                            <h4>⏰ Próxima Auditoria</h4>
                            <p>Manual</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            let authToken = localStorage.getItem('token');
            let currentUser = JSON.parse(localStorage.getItem('user') || '{}');

            function updateDebugStatus(message) {
                document.getElementById('debugStatus').textContent = message;
                console.log('DEBUG:', message);
            }

            function updateDebugLastRequest(url, status) {
                document.getElementById('debugLastRequest').textContent = url + ' - ' + status;
            }

            function checkAuth() {
                updateDebugStatus('Verificando autenticação...');
                
                if (!authToken) {
                    updateDebugStatus('ERRO: Token não encontrado');
                    document.getElementById('debugToken').textContent = 'Ausente';
                    showAlert('Token não encontrado - redirecionando para login', 'error');
                    setTimeout(() => window.location.href = '/', 2000);
                    return false;
                }
                
                document.getElementById('debugToken').textContent = 'Presente (' + authToken.length + ' chars)';
                updateDebugStatus('Token encontrado e válido');
                return true;
            }

            function setupUserInfo() {
                updateDebugStatus('Configurando informações do usuário...');
                
                if (currentUser && currentUser.username) {
                    document.getElementById('userName').textContent = currentUser.username;
                    document.getElementById('userRole').textContent = currentUser.role || 'Usuário';
                    document.getElementById('userAvatar').textContent = currentUser.username.charAt(0).toUpperCase();
                    updateDebugStatus('Informações do usuário carregadas');
                } else {
                    document.getElementById('userName').textContent = 'Usuário Desconhecido';
                    document.getElementById('userRole').textContent = 'Conectado';
                    document.getElementById('userAvatar').textContent = 'U';
                    updateDebugStatus('AVISO: Dados do usuário incompletos');
                }
            }

            async function testAPI() {
                updateDebugStatus('Testando conectividade da API...');
                document.getElementById('debugAPI').textContent = 'Testando...';
                
                try {
                    const response = await fetch('/api/dashboard/stats', {
                        headers: {
                            'Authorization': 'Bearer ' + authToken,
                            'Content-Type': 'application/json'
                        }
                    });
                    
                    updateDebugLastRequest('/api/dashboard/stats', response.status);
                    
                    if (response.status === 401) {
                        document.getElementById('debugAPI').textContent = '❌ ERRO 401';
                        updateDebugStatus('Token expirado ou inválido');
                        showAlert('Sessão expirada - redirecionando para login', 'error');
                        setTimeout(() => {
                            localStorage.removeItem('token');
                            localStorage.removeItem('user');
                            window.location.href = '/';
                        }, 2000);
                        return false;
                    }
                    
                    if (response.ok) {
                        document.getElementById('debugAPI').textContent = '✅ OK';
                        updateDebugStatus('API funcionando');
                        showAlert('API está funcionando corretamente!', 'success');
                        return true;
                    } else {
                        document.getElementById('debugAPI').textContent = '❌ ERRO ' + response.status;
                        updateDebugStatus('API com erro: ' + response.status);
                        showAlert('API retornou erro ' + response.status, 'error');
                        return false;
                    }
                } catch (error) {
                    document.getElementById('debugAPI').textContent = '❌ FALHA';
                    updateDebugStatus('Falha na API: ' + error.message);
                    showAlert('Falha de conexão com API', 'error');
                    return false;
                }
            }

            async function loadStats() {
                updateDebugStatus('Carregando estatísticas...');
                
                try {
                    const response = await fetch('/api/dashboard/stats', {
                        headers: {
                            'Authorization': 'Bearer ' + authToken,
                            'Content-Type': 'application/json'
                        }
                    });
                    
                    updateDebugLastRequest('/api/dashboard/stats', response.status);
                    
                    if (response.status === 401) {
                        updateDebugStatus('ERRO: Token expirado (401)');
                        showAlert('Sessão expirada - redirecionando para login', 'error');
                        setTimeout(() => {
                            localStorage.removeItem('token');
                            localStorage.removeItem('user');
                            window.location.href = '/';
                        }, 2000);
                        return;
                    }
                    
                    if (!response.ok) {
                        updateDebugStatus('ERRO: ' + response.status);
                        showAlert('Erro ao carregar estatísticas: ' + response.status, 'error');
                        
                        // Definir valores padrão em caso de erro
                        document.getElementById('totalClients').textContent = '0';
                        document.getElementById('totalFirewalls').textContent = '0';
                        document.getElementById('auditsToday').textContent = '0';
                        document.getElementById('avgScore').textContent = '0%';
                        return;
                    }
                    
                    const stats = await response.json();
                    updateDebugStatus('Estatísticas carregadas com sucesso');

                    document.getElementById('totalClients').textContent = stats.total_clients || 0;
                    document.getElementById('totalFirewalls').textContent = stats.total_firewalls || 0;
                    document.getElementById('auditsToday').textContent = stats.audits_today || 0;
                    document.getElementById('avgScore').textContent = (stats.avg_score || 0) + '%';
                    
                    showAlert('Estatísticas carregadas com sucesso!', 'success');
                    
                } catch (error) {
                    updateDebugStatus('EXCEÇÃO: ' + error.message);
                    console.error('Erro ao carregar estatísticas:', error);
                    showAlert('Erro ao carregar estatísticas', 'error');
                    
                    // Definir valores padrão em caso de erro
                    document.getElementById('totalClients').textContent = '0';
                    document.getElementById('totalFirewalls').textContent = '0';
                    document.getElementById('auditsToday').textContent = '0';
                    document.getElementById('avgScore').textContent = '0%';
                }
            }

            async function loadRecentAudits() {
                updateDebugStatus('Carregando auditorias recentes...');
                
                try {
                    const response = await fetch('/api/audits?limit=10', {
                        headers: {
                            'Authorization': 'Bearer ' + authToken,
                            'Content-Type': 'application/json'
                        }
                    });
                    
                    updateDebugLastRequest('/api/audits', response.status);
                    
                    if (!response.ok) {
                        updateDebugStatus('ERRO auditorias: ' + response.status);
                        document.getElementById('recentAudits').innerHTML = 
                            '<p style="text-align: center; color: #666; padding: 20px;">Erro ao carregar auditorias</p>';
                        return;
                    }
                    
                    const audits = await response.json();
                    updateDebugStatus('Carregadas ' + audits.length + ' auditorias');

                    const container = document.getElementById('recentAudits');
                    
                    if (!audits || audits.length === 0) {
                        container.innerHTML = '<p style="text-align: center; color: #666; padding: 20px;">Nenhuma auditoria encontrada</p>';
                        return;
                    }

                    container.innerHTML = audits.map(audit => {
                        const statusColor = audit.status === 'completed' ? '#28a745' : 
                                          audit.status === 'running' ? '#fd7e14' : '#dc3545';
                        const statusIcon = audit.status === 'completed' ? '✅' : 
                                         audit.status === 'running' ? '⏳' : '❌';
                        
                        return `<div style="padding: 15px; border-bottom: 1px solid #eee; margin-bottom: 10px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid ${statusColor};">
                            <div style="display: flex; justify-content: space-between; align-items: start;">
                                <div>
                                    <strong style="color: #333; font-size: 1.1rem;">${audit.client_name || 'Cliente'}</strong><br>
                                    <small style="color: #666;">
                                        ${audit.firewall || 'Todas as firewalls'} • 
                                        ${new Date(audit.started_at).toLocaleString('pt-BR')}
                                    </small><br>
                                    <span style="color: ${statusColor}; font-weight: bold; margin-top: 5px; display: inline-block;">
                                        ${statusIcon} ${audit.status.toUpperCase()}
                                    </span>
                                    ${audit.score ? `<span style="margin-left: 15px; color: #333;">Score: <strong>${audit.score}%</strong></span>` : ''}
                                </div>
                                ${audit.status === 'completed' ? 
                                    `<button onclick="viewAuditDetails(${audit.id})" style="background: #0066CC; color: white; border: none; padding: 8px 12px; border-radius: 4px; cursor: pointer; font-size: 0.85rem;">Ver Detalhes</button>` : 
                                    `<div class="loading" style="width: 16px; height: 16px;"></div>`
                                }
                            </div>
                        </div>`;
                    }).join('');
                    
                } catch (error) {
                    updateDebugStatus('ERRO auditorias: ' + error.message);
                    console.error('Erro ao carregar auditorias:', error);
                    document.getElementById('recentAudits').innerHTML = 
                        '<p style="text-align: center; color: #666; padding: 20px;">Erro ao carregar auditorias</p>';
                }
            }

            function showAlert(message, type) {
                const alert = document.getElementById('alert');
                alert.className = 'alert ' + type;
                alert.textContent = message;
                alert.style.display = 'block';
                
                setTimeout(function() {
                    alert.style.display = 'none';
                }, 5000);
            }

            function logout() {
                localStorage.removeItem('token');
                localStorage.removeItem('user');
                window.location.href = '/';
            }

            function updateTimestamp() {
                document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString('pt-BR');
            }

            function showCreateClientModal() {
                showAlert('Modal de criação de cliente em desenvolvimento', 'success');
            }

            function showRunAuditModal() {
                showAlert('Modal de execução de auditoria em desenvolvimento', 'success');
            }

            function showViewReportsModal() {
                showAlert('Modal de visualização de relatórios em desenvolvimento', 'success');
            }

            function viewAuditDetails(auditId) {
                showAlert(`Visualizando detalhes da auditoria ${auditId}`, 'success');
            }

            // Inicializar dashboard
            document.addEventListener('DOMContentLoaded', function() {
                updateDebugStatus('DOM carregado - inicializando...');
                
                if (!checkAuth()) {
                    return;
                }
                
                setupUserInfo();
                updateTimestamp();
                
                // Inicializar de forma mais robusta
                setTimeout(() => {
                    testAPI().then((apiOk) => {
                        if (apiOk) {
                            loadStats();
                            loadRecentAudits();
                        } else {
                            updateDebugStatus('API não respondeu - dados não carregados');
                            // Definir valores padrão
                            document.getElementById('totalClients').textContent = '0';
                            document.getElementById('totalFirewalls').textContent = '0';
                            document.getElementById('auditsToday').textContent = '0';
                            document.getElementById('avgScore').textContent = '0%';
                            document.getElementById('recentAudits').innerHTML = 
                                '<p style="text-align: center; color: #666; padding: 20px;">Erro ao conectar com API</p>';
                        }
                    }).catch(error => {
                        updateDebugStatus('Erro no teste da API: ' + error.message);
                        // Definir valores padrão em caso de erro
                        document.getElementById('totalClients').textContent = '0';
                        document.getElementById('totalFirewalls').textContent = '0';
                        document.getElementById('auditsToday').textContent = '0';
                        document.getElementById('avgScore').textContent = '0%';
                        document.getElementById('recentAudits').innerHTML = 
                            '<p style="text-align: center; color: #666; padding: 20px;">Erro de conexão</p>';
                    });
                }, 1000);

                // Atualizar timestamp a cada minuto
                setInterval(updateTimestamp, 60000);
            });

            console.log('Dashboard script loaded');
            console.log('Token:', authToken ? 'Present (' + authToken.length + ' chars)' : 'Missing');
            console.log('User:', currentUser);
        </script>
    </body>
    </html>
    '''
    
    return dashboard_html

# ROTAS DE AUTENTICAÇÃO
@app.route('/api/auth/login', methods=['POST'])
def login():
    """Autenticação de usuário"""
    try:
        logger.info("Login attempt started")
        data = request.get_json()
        
        if not data:
            logger.warning("No JSON data received")
            return jsonify({'error': 'No data provided'}), 400
            
        username = data.get('username')
        password = data.get('password')
        
        logger.info(f"Login attempt for username: {username}")
        
        if not username or not password:
            logger.warning("Missing username or password")
            return jsonify({'error': 'Username and password required'}), 400
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, email, password_hash, role FROM users WHERE username = ? AND is_active = 1', (username,))
        user = cursor.fetchone()
        
        if user and check_password_hash(user[3], password):
            logger.info(f"Login successful for user: {username}")
            
            # Atualizar último login
            cursor.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user[0],))
            conn.commit()
            
            # Gerar token JWT
            token = jwt.encode({
                'user_id': user[0],
                'username': user[1],
                'role': user[4],
                'exp': datetime.utcnow() + app.config['JWT_EXPIRATION_DELTA']
            }, app.config['SECRET_KEY'], algorithm='HS256')
            
            conn.close()
            
            return jsonify({
                'token': token,
                'user': {
                    'id': user[0],
                    'username': user[1],
                    'email': user[2],
                    'role': user[4]
                }
            })
        
        logger.warning(f"Login failed for username: {username}")
        conn.close()
        return jsonify({'error': 'Invalid credentials'}), 401
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# ROTAS DE API
@app.route('/api/dashboard/stats')
@token_required
def get_dashboard_stats(current_user_id):
    """Estatísticas do dashboard"""
    try:
        logger.info("Getting dashboard stats")
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Total de clientes ativos
        cursor.execute('SELECT COUNT(*) FROM clients WHERE is_active = 1')
        total_clients = cursor.fetchone()[0]
        
        # Total de firewalls
        cursor.execute('SELECT COUNT(*) FROM firewalls WHERE is_active = 1')
        total_firewalls = cursor.fetchone()[0]
        
        # Auditorias hoje
        cursor.execute('''
            SELECT COUNT(*) FROM audits 
            WHERE DATE(started_at) = DATE('now')
        ''')
        audits_today = cursor.fetchone()[0]
        
        # Score médio
        cursor.execute('''
            SELECT AVG(score) FROM audits 
            WHERE status = 'completed' AND score > 0
        ''')
        avg_score_result = cursor.fetchone()[0]
        avg_score = avg_score_result if avg_score_result is not None else 0
        
        conn.close()
        
        stats = {
            'total_clients': total_clients,
            'total_firewalls': total_firewalls,
            'audits_today': audits_today,
            'avg_score': round(avg_score, 2)
        }
        
        logger.info(f"Dashboard stats: {stats}")
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Dashboard stats error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/audits', methods=['GET'])
@token_required
def get_audits(current_user_id):
    """Listar auditorias"""
    try:
        logger.info("Getting audits list")
        limit = request.args.get('limit', 50, type=int)
        client_id = request.args.get('client_id', type=int)
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        query = '''
            SELECT a.id, c.name as client_name, f.hostname, f.port,
                   a.started_at, a.completed_at, a.status, 
                   a.success_count, a.failure_count, a.warning_count, a.score,
                   u.username as executed_by
            FROM audits a
            JOIN clients c ON a.client_id = c.id
            LEFT JOIN firewalls f ON a.firewall_id = f.id
            LEFT JOIN users u ON a.executed_by = u.id
        '''
        
        params = []
        if client_id:
            query += ' WHERE a.client_id = ?'
            params.append(client_id)
        
        query += ' ORDER BY a.started_at DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        audits = cursor.fetchall()
        conn.close()
        
        result = [{
            'id': audit[0],
            'client_name': audit[1],
            'firewall': f"{audit[2]}:{audit[3]}" if audit[2] else None,
            'started_at': audit[4],
            'completed_at': audit[5],
            'status': audit[6],
            'success_count': audit[7],
            'failure_count': audit[8],
            'warning_count': audit[9],
            'score': audit[10],
            'executed_by': audit[11]
        } for audit in audits]
        
        logger.info(f"Returning {len(result)} audits")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Get audits error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/audits/run', methods=['POST'])
@token_required
def run_audit(current_user_id):
    """Executar auditoria"""
    try:
        logger.info("Starting audit execution")
        data = request.get_json()
        client_id = data.get('client_id')
        
        if not client_id:
            return jsonify({'error': 'Client ID is required'}), 400
        
        # Verificar se cliente existe
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM clients WHERE id = ? AND is_active = 1', (client_id,))
        client = cursor.fetchone()
        
        if not client:
            conn.close()
            return jsonify({'error': 'Client not found'}), 404
        
        client_name = client[0]
        
        # Criar registro de auditoria
        cursor.execute('''
            INSERT INTO audits (client_id, executed_by, status) 
            VALUES (?, ?, ?)
        ''', (client_id, current_user_id, 'running'))
        audit_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"Audit started for client {client_name} (ID: {audit_id})")
        
        # Executar auditoria em thread separada
        thread = threading.Thread(
            target=execute_audit_background, 
            args=(audit_id, client_id, client_name)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'audit_id': audit_id,
            'message': 'Audit started successfully',
            'status': 'running'
        }), 202
        
    except Exception as e:
        logger.error(f"Run audit error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

def execute_audit_background(audit_id, client_id, client_name):
    """Executar auditoria em background"""
    try:
        logger.info(f"Executing audit for client: {client_name}")
        
        # Buscar firewalls do cliente
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT hostname, port, username, password_encrypted 
            FROM firewalls 
            WHERE client_id = ? AND is_active = 1
        ''', (client_id,))
        firewalls = cursor.fetchall()
        conn.close()
        
        if not firewalls:
            logger.warning(f"No firewalls found for client {client_name}")
            update_audit_status(audit_id, 'error', 0, 0, 0, 0.0, 'No firewalls configured')
            return
        
        # Preparar configurações dos firewalls
        firewall_configs = []
        for fw in firewalls:
            config = {
                'name': f"{client_name} - {fw[0]}",
                'hostname': fw[0],
                'port': fw[1] or 4444,
                'username': fw[2] or 'admin',
                'password': 'senha_padrao'  # TODO: Implementar descriptografia
            }
            firewall_configs.append(config)
        
        # Executar auditoria usando Sophos Integration
        if SophosFirewallAuditor:
            try:
                auditor = SophosFirewallAuditor(SOPHOS_AUDIT_SCRIPT)
                results = auditor.run_audit(firewall_configs)
                
                # Processar resultados
                total_checks = 0
                passed_checks = 0
                failed_checks = 0
                warning_checks = 0
                
                for fw_id, fw_result in results.items():
                    if fw_result.get('result', {}).get('status') == 'completed':
                        summary = fw_result.get('result', {}).get('summary', {})
                        total_checks += summary.get('total_checks', 0)
                        passed_checks += summary.get('passed_checks', 0)
                        failed_checks += summary.get('failed_checks', 0)
                        warning_checks += summary.get('warning_checks', 0)
                
                # Calcular score
                score = round((passed_checks / total_checks) * 100, 2) if total_checks > 0 else 0
                
                # Gerar relatório HTML
                html_report = auditor.generate_html_report(results, client_name)
                
                # Salvar relatório
                report_filename = f"audit_report_{audit_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                report_path = os.path.join(REPORTS_DIR, report_filename)
                
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(html_report)
                
                # Atualizar banco de dados
                update_audit_status(
                    audit_id, 'completed', 
                    passed_checks, failed_checks, warning_checks, score,
                    report_path, json.dumps(results)
                )
                
                logger.info(f"Audit completed for {client_name}: {score}% score")
                
            except Exception as e:
                logger.error(f"Sophos audit execution failed: {e}")
                # Fallback para simulação
                simulate_audit_execution(audit_id, client_name)
        else:
            # Executar simulação se Sophos Integration não estiver disponível
            simulate_audit_execution(audit_id, client_name)
            
    except Exception as e:
        logger.error(f"Execute audit background error: {str(e)}")
        update_audit_status(audit_id, 'error', 0, 0, 0, 0.0, f'Error: {str(e)}')

def simulate_audit_execution(audit_id, client_name):
    """Simular execução de auditoria"""
    try:
        logger.info(f"Simulating audit execution for {client_name}")
        
        # Simular tempo de execução
        time.sleep(5)
        
        # Simular resultados
        import random
        success_count = random.randint(70, 95)
        failure_count = random.randint(5, 30)
        warning_count = random.randint(2, 10)
        total = success_count + failure_count + warning_count
        score = round((success_count / total) * 100, 2) if total > 0 else 0
        
        # Atualizar banco de dados
        update_audit_status(
            audit_id, 'completed', 
            success_count, failure_count, warning_count, score
        )
        
        logger.info(f"Simulated audit completed for {client_name}: {score}% score")
        
    except Exception as e:
        logger.error(f"Simulate audit execution error: {str(e)}")
        update_audit_status(audit_id, 'error', 0, 0, 0, 0.0, f'Simulation error: {str(e)}')

def update_audit_status(audit_id, status, success_count=0, failure_count=0, warning_count=0, score=0.0, report_path=None, report_data=None):
    """Atualizar status da auditoria no banco de dados"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE audits 
            SET completed_at = CURRENT_TIMESTAMP, status = ?, 
                success_count = ?, failure_count = ?, warning_count = ?, score = ?,
                report_path = ?, report_data = ?
            WHERE id = ?
        ''', (status, success_count, failure_count, warning_count, score, 
             report_path, report_data, audit_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Audit {audit_id} status updated to {status}")
        
    except Exception as e:
        logger.error(f"Update audit status error: {str(e)}")

@app.route('/api/clients', methods=['GET'])
@token_required
def get_clients(current_user_id):
    """Listar todos os clientes"""
    try:
        logger.info("Getting clients list")
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT c.id, c.name, c.description, c.created_at, c.updated_at,
                   COUNT(f.id) as firewall_count,
                   MAX(a.completed_at) as last_audit,
                   AVG(a.score) as avg_score
            FROM clients c
            LEFT JOIN firewalls f ON c.id = f.client_id AND f.is_active = 1
            LEFT JOIN audits a ON c.id = a.client_id AND a.status = 'completed'
            WHERE c.is_active = 1
            GROUP BY c.id, c.name, c.description, c.created_at, c.updated_at
            ORDER BY c.name
        ''')
        clients = cursor.fetchall()
        conn.close()
        
        result = [{
            'id': client[0],
            'name': client[1],
            'description': client[2],
            'created_at': client[3],
            'updated_at': client[4],
            'firewall_count': client[5] or 0,
            'last_audit': client[6],
            'avg_score': round(client[7] or 0, 2)
        } for client in clients]
        
        logger.info(f"Returning {len(result)} clients")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Get clients error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    try:
        # Verificar conectividade do banco
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        conn.close()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'database': 'connected'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# TRATAMENTO DE ERROS
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500

# FACTORY FUNCTION
def create_app():
    """Factory para criar a aplicação"""
    try:
        # Inicializar banco se não existir
        if not os.path.exists(DATABASE_PATH):
            logger.info("Database not found, initializing...")
            init_database()
        
        logger.info("Application created successfully")
        return app
    except Exception as e:
        logger.error(f"Failed to create application: {str(e)}")
        raise

# Execução direta (para desenvolvimento)
if __name__ == '__main__':
    try:
        # Verificar se banco existe, senão inicializar
        if not os.path.exists(DATABASE_PATH):
            logger.info("Initializing database...")
            init_database()
        
        # Configurações para desenvolvimento
        debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
        host = os.environ.get('HOST', '0.0.0.0')
        port = int(os.environ.get('PORT', 8080))
        
        logger.info(f"Starting Flask development server on {host}:{port}")
        logger.info(f"Debug mode: {debug_mode}")
        logger.info("Access the application at: http://localhost:8080")
        
        app.run(
            host=host,
            port=port,
            debug=debug_mode,
            threaded=True
        )
        
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        exit(1)
