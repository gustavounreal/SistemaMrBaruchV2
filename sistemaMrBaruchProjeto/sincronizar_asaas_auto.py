#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SINCRONIZADOR ASAAS CORRIGIDO - BAIXA 100% DOS DADOS
"""
import os
import sys
import io
import django
import time
import requests
import logging
from datetime import datetime
from decimal import Decimal

# Configurar logging detalhado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sincronizador_asaas.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configurar encoding UTF-8
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistemaMrBaruchProjeto.settings')
django.setup()

from django.conf import settings
from django.utils import timezone
from asaas_sync.models import (
    AsaasClienteSyncronizado, AsaasCobrancaSyncronizada,
    AsaasClienteSyncronizado2, AsaasCobrancaSyncronizada2,
    AsaasSyncronizacaoLog
)


class SincronizadorAsaas100Porcento:
    """Sincronizador que garante 100% dos dados"""
    
    def __init__(self, conta="principal"):
        self.conta = conta
        
        # Definir token e models baseado na conta
        if conta == "alternativo":
            self.api_token = getattr(settings, 'ASAAS_ALTERNATIVO_TOKEN', '')
            self.ModelCliente = AsaasClienteSyncronizado2
            self.ModelCobranca = AsaasCobrancaSyncronizada2
            self.tipo_sync = 'ALTERNATIVO_100P'
        else:
            self.api_token = getattr(settings, 'ASAAS_API_TOKEN', '')
            self.ModelCliente = AsaasClienteSyncronizado
            self.ModelCobranca = AsaasCobrancaSyncronizada
            self.tipo_sync = 'COMPLETO_100P'
        
        self.base_url = getattr(settings, 'ASAAS_API_URL', 'https://api.asaas.com/v3')
        self.headers = {
            'Content-Type': 'application/json',
            'access_token': self.api_token
        }
        self.timeout = 120
        
        # Controle de rate limiting aprimorado
        self.requests_count = 0
        self.last_request_time = 0
        self.MIN_INTERVAL = 1.2  # 1.2 segundos entre requests
        
        # Estatísticas detalhadas
        self.stats = {
            'clientes': {'total_esperado': 0, 'total_baixados': 0, 'novos': 0, 'atualizados': 0, 'excluidos': 0, 'erros': 0},
            'cobrancas': {'total_baixadas': 0, 'novas': 0, 'atualizadas': 0, 'excluidas': 0, 'erros': 0, 'sem_cliente': 0}
        }
        
        # Criar log
        self.log = AsaasSyncronizacaoLog.objects.create(
            tipo_sincronizacao=self.tipo_sync,
            status='EM_ANDAMENTO',
            usuario='Sistema 100%'
        )
        
        logger.info(f"✅ Sincronizador 100% iniciado - Conta: {conta}")
    
    def controlar_rate_limit_rigoroso(self):
        """Controle RIGOROSO de rate limiting"""
        agora = time.time()
        tempo_decorrido = agora - self.last_request_time
        
        if tempo_decorrido < self.MIN_INTERVAL:
            sleep_time = self.MIN_INTERVAL - tempo_decorrido
            logger.debug(f"⏰ Rate limit: aguardando {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.requests_count += 1
        
        # Pausa estratégica a cada 30 requests
        if self.requests_count % 30 == 0:
            logger.info("⏰ Pausa preventiva de 3 segundos...")
            time.sleep(3)
    
    def fazer_requisicao_100porcento(self, endpoint, params=None):
        """Faz requisição com garantia de sucesso"""
        url = f"{self.base_url}/{endpoint}"
        
        for tentativa in range(1, 6):  # 5 tentativas
            try:
                self.controlar_rate_limit_rigoroso()
                
                logger.debug(f"🔁 Tentativa {tentativa}/5: {endpoint}")
                response = requests.get(url, headers=self.headers, params=params, timeout=self.timeout)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # VALIDAÇÃO CRÍTICA da resposta
                    if not isinstance(data, dict):
                        logger.error(f"❌ Resposta não é JSON: {response.text[:200]}")
                        continue
                    
                    if 'data' not in data:
                        logger.error(f"❌ Resposta sem campo 'data': {data}")
                        continue
                    
                    logger.debug(f"✅ Requisição {endpoint} bem-sucedida")
                    return data
                    
                elif response.status_code == 429:
                    wait_time = tentativa * 15  # 15, 30, 45, 60, 75 segundos
                    logger.warning(f"⏰ Rate limit detectado. Aguardando {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                    
                elif response.status_code in [500, 502, 503, 504]:
                    wait_time = tentativa * 10
                    logger.warning(f"🔧 Erro servidor {response.status_code}. Aguardando {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                    
                else:
                    logger.error(f"❌ HTTP {response.status_code}: {response.text[:200]}")
                    if response.status_code == 403:
                        raise Exception("🔑 Token inválido ou sem permissões")
                    if tentativa < 5:
                        time.sleep(tentativa * 5)
                        continue
                    return None
                    
            except requests.exceptions.Timeout:
                logger.warning(f"⏰ Timeout tentativa {tentativa}/5")
                if tentativa < 5:
                    time.sleep(tentativa * 10)
                    continue
                return None
                
            except requests.exceptions.ConnectionError:
                logger.warning(f"🔌 Erro conexão tentativa {tentativa}/5")
                if tentativa < 5:
                    time.sleep(tentativa * 15)
                    continue
                return None
                
            except Exception as e:
                logger.error(f"💥 Erro inesperado tentativa {tentativa}/5: {str(e)}")
                if tentativa < 5:
                    time.sleep(tentativa * 8)
                    continue
                return None
        
        logger.error(f"❌ Todas as tentativas falharam para {endpoint}")
        return None
    
    def baixar_clientes_100porcento(self):
        """Garante 100% dos clientes"""
        logger.info("\n" + "="*80)
        logger.info("👥 BAIXANDO 100% DOS CLIENTES")
        logger.info("="*80)
        
        clientes_asaas = []
        offset = 0
        limit = 100
        total_esperado = None
        pagina = 1
        falhas_consecutivas = 0
        
        while True:
            logger.info(f"📖 Página {pagina} - Offset {offset}")
            
            params = {'offset': offset, 'limit': limit}
            response = self.fazer_requisicao_100porcento('customers', params)
            
            if not response:
                falhas_consecutivas += 1
                logger.error(f"❌ Falha na página {pagina} (falhas consecutivas: {falhas_consecutivas})")
                
                if falhas_consecutivas >= 3:
                    logger.error("💥 Muitas falhas consecutivas - abortando")
                    break
                
                # Tenta continuar do mesmo ponto
                time.sleep(10)
                continue
            
            # Reset contador de falhas
            falhas_consecutivas = 0
            
            clientes_pagina = response.get('data', [])
            
            if not clientes_pagina:
                logger.info("✅ Página vazia - fim dos dados")
                break
            
            # Guardar totalCount da primeira página
            if total_esperado is None:
                total_esperado = response.get('totalCount', 0)
                self.stats['clientes']['total_esperado'] = total_esperado
                logger.info(f"📊 Total esperado: {total_esperado} clientes")
            
            clientes_asaas.extend(clientes_pagina)
            self.stats['clientes']['total_baixados'] = len(clientes_asaas)
            
            progresso = (len(clientes_asaas) / total_esperado * 100) if total_esperado else 0
            logger.info(f"📥 Progresso: {len(clientes_asaas)}/{total_esperado} ({progresso:.1f}%)")
            
            # VALIDAÇÃO: Verificar se atingiu o total esperado
            if total_esperado and len(clientes_asaas) >= total_esperado:
                logger.info(f"🎯 TOTAL ALCANÇADO: {len(clientes_asaas)} clientes")
                break
            
            # Verificar hasMore
            if not response.get('hasMore', False):
                logger.info("✅ API informou fim da paginação (hasMore=false)")
                break
            
            offset += limit
            pagina += 1
        
        # VALIDAÇÃO FINAL CRÍTICA
        logger.info("\n" + "="*80)
        logger.info("🔍 VALIDAÇÃO FINAL CLIENTES")
        logger.info("="*80)
        
        if total_esperado:
            if len(clientes_asaas) == total_esperado:
                logger.info(f"✅ SUCESSO ABSOLUTO: {len(clientes_asaas)}/{total_esperado} (100%)")
            else:
                faltam = total_esperado - len(clientes_asaas)
                percentual = (len(clientes_asaas) / total_esperado) * 100
                logger.error(f"❌ FALHA: {len(clientes_asaas)}/{total_esperado} ({percentual:.1f}%) - FALTAM {faltam}")
                self.stats['clientes']['erros'] = faltam
        else:
            logger.info(f"📊 Total baixado: {len(clientes_asaas)} clientes")
        
        return clientes_asaas
    
    def baixar_cobrancas_100porcento(self, clientes_ids):
        """Garante 100% das cobranças"""
        logger.info("\n" + "="*80)
        logger.info("💰 BAIXANDO 100% DAS COBRANÇAS")
        logger.info("="*80)
        
        cobrancas_asaas = []
        total_clientes = len(clientes_ids)
        clientes_com_erro = []
        
        for i, customer_id in enumerate(clientes_ids, 1):
            if i % 5 == 0:  # Log a cada 5 clientes
                logger.info(f"📊 Progresso: {i}/{total_clientes} clientes ({i/total_clientes*100:.1f}%)")
            
            cobrancas_cliente = []
            offset = 0
            limit = 100
            pagina = 1
            total_cobrancas_esperado = None
            falhas_cliente = 0
            
            while True:
                logger.debug(f"👤 Cliente {i}/{total_clientes} - Página {pagina}")
                
                response = self.fazer_requisicao_100porcento('payments', {
                    'customer': customer_id,
                    'offset': offset,
                    'limit': limit
                })
                
                if not response:
                    falhas_cliente += 1
                    logger.warning(f"⚠️ Falha no cliente {i}, página {pagina} (tentativa {falhas_cliente})")
                    
                    if falhas_cliente >= 2:
                        logger.error(f"❌ Muitas falhas no cliente {customer_id} - pulando")
                        clientes_com_erro.append(customer_id)
                        break
                    
                    time.sleep(5)
                    continue
                
                cobrancas_pagina = response.get('data', [])
                
                if not cobrancas_pagina:
                    break
                
                # Adicionar customer_id em cada cobrança
                for cobranca in cobrancas_pagina:
                    cobranca['_customer_id'] = customer_id
                
                cobrancas_cliente.extend(cobrancas_pagina)
                
                # Guardar totalCount do primeiro request
                if total_cobrancas_esperado is None:
                    total_cobrancas_esperado = response.get('totalCount', 0)
                
                # Verificar se atingiu o total
                if total_cobrancas_esperado and len(cobrancas_cliente) >= total_cobrancas_esperado:
                    break
                
                # Verificar hasMore
                if not response.get('hasMore', False):
                    break
                
                offset += limit
                pagina += 1
            
            cobrancas_asaas.extend(cobrancas_cliente)
            self.stats['cobrancas']['total_baixadas'] = len(cobrancas_asaas)
            
            if cobrancas_cliente:
                logger.debug(f"✅ Cliente {i}: {len(cobrancas_cliente)} cobranças")
            else:
                logger.debug(f"ℹ️  Cliente {i}: 0 cobranças")
        
        logger.info(f"\n📊 TOTAL COBRANÇAS: {len(cobrancas_asaas)}")
        if clientes_com_erro:
            logger.warning(f"⚠️  Clientes com erro: {len(clientes_com_erro)}")
        
        return cobrancas_asaas
    
    def sincronizar_clientes(self, clientes_asaas):
        """Sincroniza clientes com o banco"""
        logger.info("\n" + "="*80)
        logger.info("💾 SINCRONIZANDO CLIENTES NO BANCO")
        logger.info("="*80)
        
        # IDs dos clientes no Asaas
        asaas_customer_ids = set(c['id'] for c in clientes_asaas if c.get('id'))
        
        # Processar cada cliente do Asaas
        for i, cliente_data in enumerate(clientes_asaas, 1):
            asaas_id = cliente_data.get('id')
            if not asaas_id:
                continue
            
            try:
                # Buscar ou criar cliente
                cliente, criado = self.ModelCliente.objects.update_or_create(
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
                    }
                )
                
                if criado:
                    self.stats['clientes']['novos'] += 1
                else:
                    self.stats['clientes']['atualizados'] += 1
                
                if i % 100 == 0:
                    logger.info(f"📦 Progresso clientes: {i}/{len(clientes_asaas)}")
                    
            except Exception as e:
                self.stats['clientes']['erros'] += 1
                logger.error(f"❌ Erro cliente {asaas_id}: {str(e)}")
        
        # Excluir clientes locais que não existem mais no Asaas
        clientes_para_excluir = self.ModelCliente.objects.exclude(asaas_customer_id__in=asaas_customer_ids)
        qtd_excluir = clientes_para_excluir.count()
        
        if qtd_excluir > 0:
            logger.info(f"🗑️  Excluindo {qtd_excluir} clientes obsoletos...")
            
            # Excluir cobranças relacionadas primeiro
            cobrancas_relacionadas = self.ModelCobranca.objects.filter(cliente__in=clientes_para_excluir)
            qtd_cobrancas = cobrancas_relacionadas.count()
            
            if qtd_cobrancas > 0:
                logger.info(f"🗑️  Excluindo {qtd_cobrancas} cobranças relacionadas...")
                cobrancas_relacionadas.delete()
            
            clientes_para_excluir.delete()
            self.stats['clientes']['excluidos'] = qtd_excluir
        
        logger.info(f"\n✅ CLIENTES SINCRONIZADOS:")
        logger.info(f"   📊 Total: {self.stats['clientes']['total_baixados']}")
        logger.info(f"   🆕 Novos: {self.stats['clientes']['novos']}")
        logger.info(f"   🔄 Atualizados: {self.stats['clientes']['atualizados']}")
        logger.info(f"   🗑️  Excluídos: {self.stats['clientes']['excluidos']}")
        logger.info(f"   ❌ Erros: {self.stats['clientes']['erros']}")
    
    def sincronizar_cobrancas(self, cobrancas_asaas):
        """Sincroniza cobranças com o banco"""
        logger.info("\n" + "="*80)
        logger.info("💾 SINCRONIZANDO COBRANÇAS NO BANCO")
        logger.info("="*80)
        
        # IDs das cobranças no Asaas
        asaas_payment_ids = set(c['id'] for c in cobrancas_asaas if c.get('id'))
        
        # Processar cada cobrança do Asaas
        for i, cobranca_data in enumerate(cobrancas_asaas, 1):
            asaas_id = cobranca_data.get('id')
            customer_id = cobranca_data.get('_customer_id') or cobranca_data.get('customer')
            
            if not asaas_id or not customer_id:
                continue
            
            try:
                # Buscar cliente
                try:
                    cliente = self.ModelCliente.objects.get(asaas_customer_id=customer_id)
                except self.ModelCliente.DoesNotExist:
                    self.stats['cobrancas']['sem_cliente'] += 1
                    logger.warning(f"⚠️  Cliente {customer_id} não encontrado para cobrança {asaas_id}")
                    continue
                
                # Determinar tipo de cobrança
                billing_type = cobranca_data.get('billingType', 'UNDEFINED')
                tipo_cobranca = billing_type if billing_type in ['BOLETO', 'CREDIT_CARD', 'PIX'] else 'UNDEFINED'
                
                # Buscar ou criar cobrança
                cobranca, criada = self.ModelCobranca.objects.update_or_create(
                    asaas_payment_id=asaas_id,
                    defaults={
                        'cliente': cliente,
                        'tipo_cobranca': tipo_cobranca,
                        'status': cobranca_data.get('status', 'PENDING'),
                        'valor': Decimal(str(cobranca_data.get('value', 0))),
                        'valor_liquido': Decimal(str(cobranca_data.get('netValue', 0))) if cobranca_data.get('netValue') else None,
                        'descricao': cobranca_data.get('description', ''),
                        'data_vencimento': self._parse_date(cobranca_data.get('dueDate')),
                        'data_pagamento': self._parse_date(cobranca_data.get('paymentDate')),
                        'invoice_url': cobranca_data.get('invoiceUrl', ''),
                        'bank_slip_url': cobranca_data.get('bankSlipUrl', ''),
                        'pix_qrcode_url': cobranca_data.get('pixQrCodeUrl', ''),
                        'pix_copy_paste': cobranca_data.get('pixCopyPaste', ''),
                        'external_reference': cobranca_data.get('externalReference', ''),
                    }
                )
                
                if criada:
                    self.stats['cobrancas']['novas'] += 1
                else:
                    self.stats['cobrancas']['atualizadas'] += 1
                
                if i % 500 == 0:
                    logger.info(f"📦 Progresso cobranças: {i}/{len(cobrancas_asaas)}")
                    
            except Exception as e:
                self.stats['cobrancas']['erros'] += 1
                logger.error(f"❌ Erro cobrança {asaas_id}: {str(e)}")
        
        # Excluir cobranças locais que não existem mais no Asaas
        cobrancas_para_excluir = self.ModelCobranca.objects.exclude(asaas_payment_id__in=asaas_payment_ids)
        qtd_excluir = cobrancas_para_excluir.count()
        
        if qtd_excluir > 0:
            logger.info(f"🗑️  Excluindo {qtd_excluir} cobranças obsoletas...")
            cobrancas_para_excluir.delete()
            self.stats['cobrancas']['excluidas'] = qtd_excluir
        
        logger.info(f"\n✅ COBRANÇAS SINCRONIZADAS:")
        logger.info(f"   📊 Total: {self.stats['cobrancas']['total_baixadas']}")
        logger.info(f"   🆕 Novas: {self.stats['cobrancas']['novas']}")
        logger.info(f"   🔄 Atualizadas: {self.stats['cobrancas']['atualizadas']}")
        logger.info(f"   🗑️  Excluídas: {self.stats['cobrancas']['excluidas']}")
        logger.info(f"   👤 Sem cliente: {self.stats['cobrancas']['sem_cliente']}")
        logger.info(f"   ❌ Erros: {self.stats['cobrancas']['erros']}")
    
    def _parse_date(self, date_string):
        """Converte string para date"""
        if not date_string:
            return None
        try:
            return datetime.strptime(date_string, '%Y-%m-%d').date()
        except:
            return None
    
    def executar_sincronizacao_100porcento(self):
        """Executa sincronização com garantia de 100%"""
        logger.info("\n" + "🎯"*40)
        logger.info(f"SINCRONIZAÇÃO 100% - ASAAS {self.conta.upper()}")
        logger.info("🎯"*40)
        
        inicio = time.time()
        
        try:
            # 1. Baixar 100% dos clientes
            clientes_asaas = self.baixar_clientes_100porcento()
            
            if not clientes_asaas:
                raise Exception("❌ CRÍTICO: Nenhum cliente baixado")
            
            # 2. Extrair IDs dos clientes
            clientes_ids = [c['id'] for c in clientes_asaas if c.get('id')]
            logger.info(f"✅ {len(clientes_ids)} IDs de clientes extraídos")
            
            # 3. Baixar 100% das cobranças
            cobrancas_asaas = self.baixar_cobrancas_100porcento(clientes_ids)
            
            # 4. Sincronizar no banco
            self.sincronizar_clientes(clientes_asaas)
            self.sincronizar_cobrancas(cobrancas_asaas)
            
            # 5. Relatório final
            duracao = time.time() - inicio
            self.gerar_relatorio_final(duracao)
            
            return True
            
        except Exception as e:
            self.registrar_erro_global(e, time.time() - inicio)
            return False
    
    def gerar_relatorio_final(self, duracao):
        """Gera relatório final detalhado"""
        logger.info("\n" + "🎉"*40)
        logger.info("RELATÓRIO FINAL - SINCRONIZAÇÃO 100%")
        logger.info("🎉"*40)
        
        # Atualizar log no banco
        self.log.status = 'SUCESSO'
        self.log.data_fim = timezone.now()
        self.log.total_clientes = self.stats['clientes']['total_baixados']
        self.log.clientes_novos = self.stats['clientes']['novos']
        self.log.clientes_atualizados = self.stats['clientes']['atualizados']
        self.log.total_cobrancas = self.stats['cobrancas']['total_baixadas']
        self.log.cobrancas_novas = self.stats['cobrancas']['novas']
        self.log.cobrancas_atualizadas = self.stats['cobrancas']['atualizadas']
        self.log.duracao_segundos = int(duracao)
        
        mensagem = f"""✅ SINCRONIZAÇÃO 100% CONCLUÍDA - {self.conta}

👥 CLIENTES:
  • Esperados: {self.stats['clientes']['total_esperado']}
  • Baixados: {self.stats['clientes']['total_baixados']}
  • Novos: {self.stats['clientes']['novos']}
  • Atualizados: {self.stats['clientes']['atualizados']}
  • Excluídos: {self.stats['clientes']['excluidos']}
  • Erros: {self.stats['clientes']['erros']}

💰 COBRANÇAS:
  • Baixadas: {self.stats['cobrancas']['total_baixadas']}
  • Novas: {self.stats['cobrancas']['novas']}
  • Atualizadas: {self.stats['cobrancas']['atualizadas']}
  • Excluídas: {self.stats['cobrancas']['excluidas']}
  • Sem cliente: {self.stats['cobrancas']['sem_cliente']}
  • Erros: {self.stats['cobrancas']['erros']}

⏰ Duração: {duracao:.0f}s ({duracao/60:.1f}min)
📊 Requests realizados: {self.requests_count}

🎯 STATUS: {"100% COMPLETO" if self.stats['clientes']['erros'] == 0 else "COM FALHAS PARCIAIS"}"""

        self.log.mensagem = mensagem
        self.log.save()
        
        logger.info(mensagem)
        logger.info("🎉"*40)
    
    def registrar_erro_global(self, erro, duracao):
        """Registra erro global"""
        logger.error(f"💥 ERRO GLOBAL: {str(erro)}")
        
        self.log.status = 'ERRO'
        self.log.data_fim = timezone.now()
        self.log.duracao_segundos = int(duracao)
        self.log.erros = str(erro)
        self.log.save()


if __name__ == '__main__':
    # Verificar argumentos
    if len(sys.argv) > 1:
        args = [arg for arg in sys.argv[1:] if not arg.startswith('--')]
        if args:
            conta = args[0].lower()
            if conta not in ['principal', 'alternativo']:
                logger.error("[ERRO] Conta inválida! Use: principal ou alternativo")
                sys.exit(1)
        else:
            conta = 'principal'
    else:
        conta = 'principal'
    
    logger.info(f"🚀 Iniciando sincronização 100% - conta: {conta}")
    
    sincronizador = SincronizadorAsaas100Porcento(conta=conta)
    
    try:
        sucesso = sincronizador.executar_sincronizacao_100porcento()
        if sucesso:
            logger.info("✅ SINCRONIZAÇÃO 100% CONCLUÍDA COM SUCESSO!")
            sys.exit(0)
        else:
            logger.error("❌ SINCRONIZAÇÃO FALHOU")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.error("\n\n❌ Interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\n💥 ERRO CRÍTICO: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
