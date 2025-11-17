"""
SCRIPT 2: Importar JSON para o banco de dados
Uso: python importar_json_banco.py <arquivo.json>
Exemplo:
  python importar_json_banco.py asaas_principal_20251117_193000.json
"""
import os
import sys
import django
import json
from decimal import Decimal
from datetime import datetime

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistemaMrBaruchProjeto.settings')
django.setup()

from django.utils import timezone
from asaas_sync.models import AsaasClienteSyncronizado, AsaasCobrancaSyncronizada, AsaasSyncronizacaoLog


class ImportadorJSON:
    def __init__(self, arquivo_json):
        self.arquivo_json = arquivo_json
        self.dados = None
        
    def carregar_json(self):
        """Carrega arquivo JSON"""
        print("\n" + "="*80)
        print("📂 CARREGANDO ARQUIVO JSON")
        print("="*80)
        
        if not os.path.exists(self.arquivo_json):
            raise FileNotFoundError(f"Arquivo não encontrado: {self.arquivo_json}")
        
        tamanho_mb = os.path.getsize(self.arquivo_json) / (1024 * 1024)
        print(f"📄 Arquivo: {self.arquivo_json}")
        print(f"📊 Tamanho: {tamanho_mb:.2f} MB")
        
        with open(self.arquivo_json, 'r', encoding='utf-8') as f:
            self.dados = json.load(f)
        
        print(f"✅ JSON carregado!")
        print(f"📊 Conta: {self.dados.get('conta', 'N/A')}")
        print(f"📊 Data download: {self.dados.get('data_download', 'N/A')}")
        print(f"📊 Clientes: {self.dados.get('total_clientes', 0)}")
        print(f"📊 Cobranças: {self.dados.get('total_cobrancas', 0)}")
        
        # Validar estrutura do JSON
        print("\n🔍 Validando estrutura do JSON...")
        validacao = self.dados.get('validacao', {})
        
        if validacao:
            print(f"✅ Download completo: {validacao.get('download_completo', False)}")
            print(f"✅ Clientes únicos: {validacao.get('clientes_unicos', 0)}")
            print(f"✅ Cobranças únicas: {validacao.get('cobrancas_unicas', 0)}")
        
        if self.dados.get('cobrancas_por_status'):
            print(f"\n📊 Cobranças por status:")
            for status, qtd in self.dados['cobrancas_por_status'].items():
                print(f"   • {status}: {qtd}")
        
        if self.dados.get('valor_total_cobrancas'):
            print(f"\n💰 Valor total: R$ {self.dados['valor_total_cobrancas']:,.2f}")
        
    def importar_clientes(self):
        """Importa clientes para o banco"""
        print("\n" + "="*80)
        print("💾 IMPORTANDO CLIENTES")
        print("="*80)
        
        clientes_data = self.dados.get('clientes', [])
        stats = {'total': 0, 'novos': 0, 'atualizados': 0, 'erros': 0}
        
        for i, cliente_data in enumerate(clientes_data, 1):
            try:
                asaas_id = cliente_data.get('id')
                
                if not asaas_id:
                    stats['erros'] += 1
                    continue
                
                # Salvar ou atualizar
                cliente, created = AsaasClienteSyncronizado.objects.update_or_create(
                    asaas_customer_id=asaas_id,
                    defaults={
                        'nome': cliente_data.get('name', ''),
                        'cpf_cnpj': cliente_data.get('cpfCnpj', ''),
                        'email': cliente_data.get('email', ''),
                        'telefone': cliente_data.get('phone', ''),
                        'celular': cliente_data.get('mobilePhone', ''),
                        'cep': cliente_data.get('postalCode', ''),
                        'endereco': cliente_data.get('address', ''),
                        'numero': cliente_data.get('addressNumber', ''),
                        'complemento': cliente_data.get('complement', ''),
                        'bairro': cliente_data.get('province', ''),
                        'cidade': cliente_data.get('city', ''),
                        'estado': cliente_data.get('state', ''),
                        'inscricao_municipal': cliente_data.get('municipalInscription', ''),
                        'inscricao_estadual': cliente_data.get('stateInscription', ''),
                        'observacoes': cliente_data.get('observations', ''),
                        'external_reference': cliente_data.get('externalReference', ''),
                        'notificacoes_desabilitadas': cliente_data.get('notificationDisabled', False),
                        'data_criacao_asaas': self._parse_datetime(cliente_data.get('dateCreated')),
                    }
                )
                
                stats['total'] += 1
                if created:
                    stats['novos'] += 1
                else:
                    stats['atualizados'] += 1
                
                if i % 100 == 0:
                    print(f"  📊 Progresso: {i}/{len(clientes_data)} ({(i/len(clientes_data)*100):.1f}%)")
                    
            except Exception as e:
                stats['erros'] += 1
                print(f"  ❌ Erro no cliente {cliente_data.get('id', 'N/A')}: {str(e)}")
        
        print(f"\n✅ CLIENTES IMPORTADOS:")
        print(f"   Total: {stats['total']}")
        print(f"   Novos: {stats['novos']}")
        print(f"   Atualizados: {stats['atualizados']}")
        print(f"   Erros: {stats['erros']}")
        
        return stats
    
    def importar_cobrancas(self):
        """Importa cobranças para o banco"""
        print("\n" + "="*80)
        print("💾 IMPORTANDO COBRANÇAS")
        print("="*80)
        
        cobrancas_data = self.dados.get('cobrancas', [])
        stats = {'total': 0, 'novas': 0, 'atualizadas': 0, 'erros': 0, 'sem_cliente': 0}
        
        for i, cobranca_data in enumerate(cobrancas_data, 1):
            try:
                asaas_payment_id = cobranca_data.get('id')
                customer_id = cobranca_data.get('_customer_id') or cobranca_data.get('customer')
                
                if not asaas_payment_id:
                    stats['erros'] += 1
                    continue
                
                # Buscar cliente no banco
                try:
                    cliente = AsaasClienteSyncronizado.objects.get(asaas_customer_id=customer_id)
                except AsaasClienteSyncronizado.DoesNotExist:
                    stats['sem_cliente'] += 1
                    continue
                
                # Salvar ou atualizar cobrança
                cobranca, created = AsaasCobrancaSyncronizada.objects.update_or_create(
                    asaas_payment_id=asaas_payment_id,
                    defaults={
                        'cliente': cliente,
                        'tipo_cobranca': cobranca_data.get('billingType', 'UNDEFINED'),
                        'status': cobranca_data.get('status', 'PENDING'),
                        'valor': Decimal(str(cobranca_data.get('value', 0))),
                        'valor_liquido': Decimal(str(cobranca_data.get('netValue', 0))) if cobranca_data.get('netValue') else None,
                        'descricao': cobranca_data.get('description', ''),
                        'data_vencimento': self._parse_date(cobranca_data.get('dueDate')),
                        'data_pagamento': self._parse_date(cobranca_data.get('paymentDate')),
                        'data_criacao_asaas': self._parse_datetime(cobranca_data.get('dateCreated')),
                        'invoice_url': cobranca_data.get('invoiceUrl', ''),
                        'bank_slip_url': cobranca_data.get('bankSlipUrl', ''),
                        'pix_qrcode_url': cobranca_data.get('pixQrCodeUrl', ''),
                        'pix_copy_paste': cobranca_data.get('pixCopyAndPaste', ''),
                        'numero_parcela': cobranca_data.get('installmentNumber'),
                        'total_parcelas': cobranca_data.get('installmentCount'),
                        'external_reference': cobranca_data.get('externalReference', ''),
                    }
                )
                
                stats['total'] += 1
                if created:
                    stats['novas'] += 1
                else:
                    stats['atualizadas'] += 1
                
                if i % 500 == 0:
                    print(f"  📊 Progresso: {i}/{len(cobrancas_data)} ({(i/len(cobrancas_data)*100):.1f}%)")
                    
            except Exception as e:
                stats['erros'] += 1
                print(f"  ❌ Erro na cobrança {cobranca_data.get('id', 'N/A')}: {str(e)}")
        
        print(f"\n✅ COBRANÇAS IMPORTADAS:")
        print(f"   Total: {stats['total']}")
        print(f"   Novas: {stats['novas']}")
        print(f"   Atualizadas: {stats['atualizadas']}")
        print(f"   Sem cliente: {stats['sem_cliente']}")
        print(f"   Erros: {stats['erros']}")
        
        return stats
    
    def criar_log(self, stats_clientes, stats_cobrancas, duracao):
        """Cria log da importação"""
        log = AsaasSyncronizacaoLog.objects.create(
            tipo_sincronizacao='IMPORTACAO_JSON',
            status='SUCESSO',
            usuario='Sistema',
            total_clientes=stats_clientes['total'],
            clientes_novos=stats_clientes['novos'],
            clientes_atualizados=stats_clientes['atualizados'],
            total_cobrancas=stats_cobrancas['total'],
            cobrancas_novas=stats_cobrancas['novas'],
            cobrancas_atualizadas=stats_cobrancas['atualizadas'],
            duracao_segundos=int(duracao),
            mensagem=f"""✅ Importação JSON concluída - {self.dados.get('conta', 'N/A')}

📂 Arquivo: {os.path.basename(self.arquivo_json)}
📅 Download em: {self.dados.get('data_download', 'N/A')}

💾 CLIENTES:
   • Total: {stats_clientes['total']} ({stats_clientes['novos']} novos, {stats_clientes['atualizados']} atualizados)
   • Erros: {stats_clientes['erros']}

💾 COBRANÇAS:
   • Total: {stats_cobrancas['total']} ({stats_cobrancas['novas']} novas, {stats_cobrancas['atualizadas']} atualizadas)
   • Sem cliente: {stats_cobrancas['sem_cliente']}
   • Erros: {stats_cobrancas['erros']}

⏱️  Duração: {duracao:.0f} segundos"""
        )
        
        return log
    
    def executar(self):
        """Executa importação completa"""
        import time
        
        print("\n" + "🚀"*40)
        print("IMPORTAR JSON PARA BANCO DE DADOS")
        print("🚀"*40)
        
        inicio = time.time()
        
        # Carregar JSON
        self.carregar_json()
        
        # Importar dados
        stats_clientes = self.importar_clientes()
        stats_cobrancas = self.importar_cobrancas()
        
        # Criar log
        duracao = time.time() - inicio
        log = self.criar_log(stats_clientes, stats_cobrancas, duracao)
        
        print("\n" + "🎉"*40)
        print("IMPORTAÇÃO CONCLUÍDA!")
        print(f"⏱️  Tempo: {duracao:.0f} segundos ({duracao/60:.1f} minutos)")
        print(f"📝 Log ID: {log.id}")
        print("🎉"*40)
    
    def _parse_date(self, date_string):
        """Converte string para date"""
        if not date_string:
            return None
        try:
            return datetime.strptime(date_string, '%Y-%m-%d').date()
        except:
            return None
    
    def _parse_datetime(self, datetime_string):
        """Converte string para datetime com timezone"""
        if not datetime_string:
            return None
        try:
            dt = datetime.strptime(datetime_string, '%Y-%m-%d %H:%M:%S')
            return timezone.make_aware(dt)
        except:
            try:
                dt = datetime.strptime(datetime_string, '%Y-%m-%d')
                return timezone.make_aware(dt)
            except:
                return None


if __name__ == '__main__':
    # Verificar argumentos
    if len(sys.argv) < 2:
        print("❌ Uso: python importar_json_banco.py <arquivo.json>")
        sys.exit(1)
    
    arquivo = sys.argv[1]
    
    if not os.path.exists(arquivo):
        print(f"❌ Arquivo não encontrado: {arquivo}")
        sys.exit(1)
    
    print(f"\n🎯 Arquivo: {arquivo}")
    
    if not input("\n⚠️  Isso vai IMPORTAR os dados para o banco. Continuar? (s/n): ").lower().startswith('s'):
        print("❌ Cancelado pelo usuário")
        sys.exit(0)
    
    # Executar
    importador = ImportadorJSON(arquivo)
    
    try:
        importador.executar()
        print("\n✅ Sucesso!")
    except KeyboardInterrupt:
        print("\n\n❌ Interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ ERRO: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
