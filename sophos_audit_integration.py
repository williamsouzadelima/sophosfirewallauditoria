# sophos_audit_integration.py
# Integração com o projeto oficial Sophos Firewall Audit
# https://github.com/sophos/sophos-firewall-audit

import os
import json
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import yaml
import logging

logger = logging.getLogger(__name__)

class SophosFirewallAuditor:
    """
    Classe para integração com o Sophos Firewall Audit oficial
    """
    
    def __init__(self, audit_script_path: str = None):
        """
        Inicializar o auditor
        
        Args:
            audit_script_path: Caminho para o script de auditoria do Sophos
        """
        self.audit_script_path = audit_script_path or self._find_audit_script()
        self.temp_dir = None
        
    def _find_audit_script(self) -> str:
        """
        Encontrar o script de auditoria do Sophos
        """
        possible_paths = [
            './sophos-firewall-audit/sophos_firewall_audit.py',
            './multi_client_audit.sh',
            '/opt/sophos-audit/sophos_firewall_audit.py',
            os.path.join(os.getcwd(), 'sophos_firewall_audit.py')
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Found Sophos audit script at: {path}")
                return path
                
        # Se não encontrar, fazer download do GitHub
        return self._download_sophos_audit()
    
    def _download_sophos_audit(self) -> str:
        """
        Fazer download do script oficial do GitHub
        """
        try:
            import git
            
            repo_url = "https://github.com/sophos/sophos-firewall-audit.git"
            clone_dir = "./sophos-firewall-audit"
            
            if os.path.exists(clone_dir):
                shutil.rmtree(clone_dir)
            
            logger.info(f"Cloning Sophos Firewall Audit from {repo_url}")
            git.Repo.clone_from(repo_url, clone_dir)
            
            script_path = os.path.join(clone_dir, "sophos_firewall_audit.py")
            
            if os.path.exists(script_path):
                logger.info(f"Successfully downloaded Sophos audit script to: {script_path}")
                return script_path
            else:
                raise FileNotFoundError("Script not found in repository")
                
        except ImportError:
            logger.error("GitPython not installed. Please install with: pip install GitPython")
            raise
        except Exception as e:
            logger.error(f"Failed to download Sophos audit script: {e}")
            raise
    
    def prepare_audit_config(self, firewall_config: Dict) -> str:
        """
        Preparar arquivo de configuração para auditoria
        
        Args:
            firewall_config: Configuração do firewall
            
        Returns:
            Caminho para o arquivo de configuração
        """
        if not self.temp_dir:
            self.temp_dir = tempfile.mkdtemp(prefix='sophos_audit_')
        
        config_file = os.path.join(self.temp_dir, 'audit_config.yaml')
        
        # Estrutura de configuração baseada no projeto oficial
        config = {
            'firewalls': [
                {
                    'name': firewall_config.get('name', 'Firewall'),
                    'host': firewall_config.get('hostname'),
                    'port': firewall_config.get('port', 4444),
                    'username': firewall_config.get('username'),
                    'password': firewall_config.get('password'),
                    'enable_https': firewall_config.get('enable_https', True),
                    'verify_ssl': firewall_config.get('verify_ssl', False)
                }
            ],
            'audit_options': {
                'output_format': 'json',
                'include_sensitive': False,
                'parallel_execution': True,
                'timeout': 300,
                'retry_attempts': 3
            },
            'checks': {
                'security_policies': True,
                'system_configuration': True,
                'network_settings': True,
                'user_authentication': True,
                'logging_configuration': True,
                'update_status': True,
                'certificate_validation': True,
                'intrusion_prevention': True,
                'web_filtering': True,
                'application_control': True
            }
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        
        logger.info(f"Created audit configuration: {config_file}")
        return config_file
    
    def run_audit(self, firewall_configs: List[Dict]) -> Dict:
        """
        Executar auditoria usando o script oficial do Sophos
        
        Args:
            firewall_configs: Lista de configurações de firewalls
            
        Returns:
            Resultados da auditoria
        """
        try:
            if not self.temp_dir:
                self.temp_dir = tempfile.mkdtemp(prefix='sophos_audit_')
            
            results = {}
            
            for idx, firewall_config in enumerate(firewall_configs):
                logger.info(f"Starting audit for firewall: {firewall_config.get('hostname')}")
                
                # Preparar configuração específica
                config_file = self.prepare_audit_config(firewall_config)
                
                # Executar auditoria
                result = self._execute_audit_script(config_file, firewall_config)
                
                results[f"firewall_{idx}"] = {
                    'hostname': firewall_config.get('hostname'),
                    'name': firewall_config.get('name', f'Firewall {idx+1}'),
                    'result': result
                }
            
            return results
            
        except Exception as e:
            logger.error(f"Audit execution failed: {e}")
            raise
        finally:
            self._cleanup_temp_files()
    
    def _execute_audit_script(self, config_file: str, firewall_config: Dict) -> Dict:
        """
        Executar o script de auditoria
        
        Args:
            config_file: Caminho para arquivo de configuração
            firewall_config: Configuração do firewall
            
        Returns:
            Resultado da auditoria
        """
        try:
            # Preparar comando
            if self.audit_script_path.endswith('.py'):
                cmd = [
                    'python3', 
                    self.audit_script_path,
                    '--config', config_file,
                    '--output-format', 'json',
                    '--host', firewall_config.get('hostname'),
                    '--port', str(firewall_config.get('port', 4444)),
                    '--username', firewall_config.get('username'),
                    '--password', firewall_config.get('password')
                ]
            else:
                # Script shell
                cmd = [
                    'bash',
                    self.audit_script_path,
                    firewall_config.get('hostname'),
                    str(firewall_config.get('port', 4444)),
                    firewall_config.get('username'),
                    firewall_config.get('password')
                ]
            
            # Executar comando
            logger.info(f"Executing audit command: {' '.join(cmd[:4])}...")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutos timeout
                cwd=self.temp_dir
            )
            
            if result.returncode == 0:
                # Tentar parsear JSON
                try:
                    audit_result = json.loads(result.stdout)
                    return self._process_audit_result(audit_result)
                except json.JSONDecodeError:
                    # Se não for JSON, processar como texto
                    return self._process_text_result(result.stdout)
            else:
                logger.error(f"Audit script failed: {result.stderr}")
                return {
                    'status': 'error',
                    'error': result.stderr,
                    'return_code': result.returncode
                }
                
        except subprocess.TimeoutExpired:
            logger.error("Audit script timed out")
            return {
                'status': 'timeout',
                'error': 'Audit execution timed out after 5 minutes'
            }
        except Exception as e:
            logger.error(f"Error executing audit script: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _process_audit_result(self, audit_result: Dict) -> Dict:
        """
        Processar resultado da auditoria em formato JSON
        
        Args:
            audit_result: Resultado bruto da auditoria
            
        Returns:
            Resultado processado
        """
        try:
            # Estrutura padrão do resultado
            processed = {
                'status': 'completed',
                'timestamp': audit_result.get('timestamp'),
                'summary': {
                    'total_checks': 0,
                    'passed_checks': 0,
                    'failed_checks': 0,
                    'warning_checks': 0,
                    'score': 0.0
                },
                'categories': {},
                'recommendations': [],
                'raw_data': audit_result
            }
            
            # Processar categorias de verificação
            checks = audit_result.get('checks', {})
            
            for category, category_data in checks.items():
                if isinstance(category_data, dict):
                    category_result = self._process_category(category_data)
                    processed['categories'][category] = category_result
                    
                    # Atualizar contadores
                    processed['summary']['total_checks'] += category_result.get('total', 0)
                    processed['summary']['passed_checks'] += category_result.get('passed', 0)
                    processed['summary']['failed_checks'] += category_result.get('failed', 0)
                    processed['summary']['warning_checks'] += category_result.get('warnings', 0)
            
            # Calcular score geral
            total = processed['summary']['total_checks']
            passed = processed['summary']['passed_checks']
            
            if total > 0:
                processed['summary']['score'] = round((passed / total) * 100, 2)
            
            # Extrair recomendações
            processed['recommendations'] = self._extract_recommendations(audit_result)
            
            return processed
            
        except Exception as e:
            logger.error(f"Error processing audit result: {e}")
            return {
                'status': 'error',
                'error': f'Failed to process audit result: {e}',
                'raw_data': audit_result
            }
    
    def _process_category(self, category_data: Dict) -> Dict:
        """
        Processar dados de uma categoria específica
        """
        result = {
            'name': category_data.get('name', 'Unknown Category'),
            'description': category_data.get('description', ''),
            'total': 0,
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'checks': []
        }
        
        checks = category_data.get('checks', [])
        
        for check in checks:
            check_result = {
                'name': check.get('name'),
                'description': check.get('description'),
                'status': check.get('status'),
                'severity': check.get('severity', 'medium'),
                'recommendation': check.get('recommendation'),
                'details': check.get('details')
            }
            
            result['checks'].append(check_result)
            result['total'] += 1
            
            if check.get('status') == 'passed':
                result['passed'] += 1
            elif check.get('status') == 'failed':
                result['failed'] += 1
            elif check.get('status') == 'warning':
                result['warnings'] += 1
        
        return result
    
    def _process_text_result(self, text_output: str) -> Dict:
        """
        Processar resultado em formato texto
        """
        # Implementar parser para saída em texto
        # Esta é uma versão simplificada
        lines = text_output.strip().split('\n')
        
        result = {
            'status': 'completed',
            'summary': {
                'total_checks': 0,
                'passed_checks': 0,
                'failed_checks': 0,
                'warning_checks': 0,
                'score': 0.0
            },
            'raw_output': text_output
        }
        
        # Análise básica do texto
        for line in lines:
            if 'PASS' in line.upper():
                result['summary']['passed_checks'] += 1
            elif 'FAIL' in line.upper():
                result['summary']['failed_checks'] += 1
            elif 'WARN' in line.upper():
                result['summary']['warning_checks'] += 1
        
        total = (result['summary']['passed_checks'] + 
                result['summary']['failed_checks'] + 
                result['summary']['warning_checks'])
        
        result['summary']['total_checks'] = total
        
        if total > 0:
            result['summary']['score'] = round(
                (result['summary']['passed_checks'] / total) * 100, 2
            )
        
        return result
    
    def _extract_recommendations(self, audit_result: Dict) -> List[Dict]:
        """
        Extrair recomendações do resultado da auditoria
        """
        recommendations = []
        
        # Buscar recomendações em diferentes seções
        for category, category_data in audit_result.get('checks', {}).items():
            if isinstance(category_data, dict):
                checks = category_data.get('checks', [])
                
                for check in checks:
                    if check.get('status') == 'failed' and check.get('recommendation'):
                        recommendations.append({
                            'category': category,
                            'check': check.get('name'),
                            'severity': check.get('severity', 'medium'),
                            'recommendation': check.get('recommendation'),
                            'priority': self._calculate_priority(check)
                        })
        
        # Ordenar por prioridade
        recommendations.sort(key=lambda x: x['priority'], reverse=True)
        
        return recommendations
    
    def _calculate_priority(self, check: Dict) -> int:
        """
        Calcular prioridade da recomendação
        """
        severity_weights = {
            'critical': 10,
            'high': 8,
            'medium': 5,
            'low': 2,
            'info': 1
        }
        
        return severity_weights.get(check.get('severity', 'medium'), 5)
    
    def _cleanup_temp_files(self):
        """
        Limpar arquivos temporários
        """
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp directory: {e}")
            finally:
                self.temp_dir = None
    
    def generate_html_report(self, audit_results: Dict, client_name: str) -> str:
        """
        Gerar relatório HTML baseado nos resultados
        
        Args:
            audit_results: Resultados da auditoria
            client_name: Nome do cliente
            
        Returns:
            HTML do relatório
        """
        from datetime import datetime
        
        # Calcular estatísticas gerais
        total_firewalls = len(audit_results)
        total_checks = sum(fw.get('result', {}).get('summary', {}).get('total_checks', 0) 
                          for fw in audit_results.values())
        total_passed = sum(fw.get('result', {}).get('summary', {}).get('passed_checks', 0) 
                          for fw in audit_results.values())
        total_failed = sum(fw.get('result', {}).get('summary', {}).get('failed_checks', 0) 
                          for fw in audit_results.values())
        
        overall_score = round((total_passed / total_checks) * 100, 2) if total_checks > 0 else 0
        
        # Template HTML
        html_template = f"""
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Relatório Sophos Firewall Audit - {client_name}</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
                .container {{ max-width: 1000px; margin: 0 auto; background: white; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); overflow: hidden; }}
                .header {{ background: linear-gradient(135deg, #0066CC, #004499); color: white; padding: 30px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 2.5rem; }}
                .header p {{ margin: 10px 0 0 0; opacity: 0.9; font-size: 1.1rem; }}
                .content {{ padding: 30px; }}
                .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
                .stat-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; border-left: 4px solid #0066CC; }}
                .stat-value {{ font-size: 2rem; font-weight: bold; color: #333; margin-bottom: 5px; }}
                .stat-label {{ color: #666; font-size: 0.9rem; }}
                .score {{ font-size: 4rem; font-weight: bold; color: {'#28a745' if overall_score >= 80 else '#ffc107' if overall_score >= 60 else '#dc3545'}; text-align: center; margin: 30px 0; }}
                .firewall-section {{ margin-bottom: 30px; padding: 20px; background: #f8f9fa; border-radius: 8px; }}
                .firewall-title {{ font-size: 1.3rem; font-weight: bold; color: #333; margin-bottom: 15px; }}
                .categories {{ display: grid; gap: 15px; }}
                .category {{ background: white; padding: 15px; border-radius: 6px; border-left: 3px solid #0066CC; }}
                .category-name {{ font-weight: bold; color: #333; margin-bottom: 10px; }}
                .category-stats {{ font-size: 0.9rem; color: #666; }}
                .recommendations {{ background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 8px; padding: 20px; margin-top: 20px; }}
                .recommendations h3 {{ color: #856404; margin-top: 0; }}
                .recommendation {{ background: white; padding: 10px; margin: 10px 0; border-radius: 4px; border-left: 3px solid #ffc107; }}
                .footer {{ text-align: center; padding: 20px; color: #666; border-top: 1px solid #eee; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Sophos Firewall Audit Report</h1>
                    <p>Cliente: {client_name}</p>
                    <p>Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}</p>
                </div>
                
                <div class="content">
                    <div class="score">{overall_score:.1f}%</div>
                    <p style="text-align: center; color: #666; margin-top: -10px; margin-bottom: 30px;">Score Geral de Segurança</p>
                    
                    <div class="summary">
                        <div class="stat-card">
                            <div class="stat-value">{total_firewalls}</div>
                            <div class="stat-label">Firewalls Auditados</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{total_checks}</div>
                            <div class="stat-label">Total de Verificações</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{total_passed}</div>
                            <div class="stat-label">Verificações Aprovadas</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{total_failed}</div>
                            <div class="stat-label">Verificações Reprovadas</div>
                        </div>
                    </div>
        """
        
        # Adicionar seções dos firewalls
        for fw_id, fw_data in audit_results.items():
            fw_name = fw_data.get('name', fw_data.get('hostname', 'Firewall'))
            fw_result = fw_data.get('result', {})
            fw_summary = fw_result.get('summary', {})
            fw_categories = fw_result.get('categories', {})
            
            html_template += f"""
                    <div class="firewall-section">
                        <div class="firewall-title">🛡️ {fw_name}</div>
                        <div class="categories">
            """
            
            for cat_name, cat_data in fw_categories.items():
                html_template += f"""
                            <div class="category">
                                <div class="category-name">{cat_name.replace('_', ' ').title()}</div>
                                <div class="category-stats">
                                    ✅ {cat_data.get('passed', 0)} aprovadas | 
                                    ❌ {cat_data.get('failed', 0)} reprovadas | 
                                    ⚠️ {cat_data.get('warnings', 0)} avisos
                                </div>
                            </div>
                """
            
            html_template += """
                        </div>
                    </div>
            """
        
        # Finalizar HTML
        html_template += """
                </div>
                
                <div class="footer">
                    <p>Relatório gerado pelo Strati Audit System usando Sophos Firewall Audit oficial</p>
                    <p>https://github.com/sophos/sophos-firewall-audit</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_template

# Exemplo de uso
if __name__ == "__main__":
    # Configuração de teste
    firewall_config = {
        'name': 'Firewall Principal',
        'hostname': '192.168.1.1',
        'port': 4444,
        'username': 'admin',
        'password': 'senha123'
    }
    
    # Criar auditor
    auditor = SophosFirewallAuditor()
    
    # Executar auditoria
    try:
        results = auditor.run_audit([firewall_config])
        print("Auditoria concluída com sucesso!")
        print(json.dumps(results, indent=2))
        
        # Gerar relatório HTML
        html_report = auditor.generate_html_report(results, "Cliente Teste")
        
        with open('relatorio_sophos.html', 'w', encoding='utf-8') as f:
            f.write(html_report)
        
        print("Relatório HTML gerado: relatorio_sophos.html")
        
    except Exception as e:
        print(f"Erro na auditoria: {e}")
