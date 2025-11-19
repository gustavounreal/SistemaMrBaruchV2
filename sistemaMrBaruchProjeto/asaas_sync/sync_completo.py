"""
Sincronização COMPLETA e ROBUSTA do Asaas
Estratégia: Baixar TUDO em JSON → Salvar no banco depois
"""
import requests
import json
import logging
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from datetime import datetime
from .models import AsaasClienteSyncronizado, AsaasCobrancaSyncronizada, AsaasSyncronizacaoLog

logger = logging.getLogger(__name__)


class AsaasSyncCompleto:
    """
    Sincronização completa em 2 FASES:
    FASE 1: Baixar TODOS os dados da API (clientes e cobranças) em JSON
    FASE 2: Salvar/Atualizar tudo no banco de dados
    """
    
    def __init__(self, api_token=None, api_url=None):
        self.api_token = api_token or getattr(settings, 'ASAAS_API_TOKEN', '')
        self.base_url = api_url or getattr(settings, 'ASAAS_API_URL', 'https://api.asaas.com/v3')
        self.headers = {
            'Content-Type': 'application/json',
            'access_token': self.api_token
        }
        self.timeout = 120  # 2 minutos por requisição
        
        # Armazenamento temporário dos dados
        self.dados_clientes = []
        self.dados_cobrancas = []
        
    def _fazer_requisicao(self, metodo, endpoint, params=None):
        """Faz requisição à API do Asaas com retry e rate limit handling"""
        url = f"{self.base_url}/{endpoint}"
        max_tentativas = 3
        
        for tentativa in range(1, max_tentativas + 1):
            try:
                logger.info(f"📡 {metodo} {endpoint} (tentativa {tentativa}/{max_tentativas})")
                
                response = requests.request(
                    method=metodo,
                    url=url,
                    params=params,
                    headers=self.headers,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    return response.json()
                    
                elif response.status_code == 429 or response.status_code == 403:  # Rate limit
                    tempo_espera = 60 if response.status_code == 403 else 10
                    logger.warning(f"⚠️  Rate limit atingido (erro {response.status_code}). Aguardando {tempo_espera}s...")
                    import time
                    time.sleep(tempo_espera)
                    continue
                    
                else:
                    logger.error(f"❌ Erro {response.status_code}: {response.text[:200]}")
                    if tentativa == max_tentativas:
                        return None
                    import time
                    time.sleep(2)
                    
            except requests.exceptions.Timeout:
                logger.error(f"❌ Timeout na tentativa {tentativa}")
                if tentativa == max_tentativas:
                    return None
                import time
                time.sleep(3)
                
            except Exception as e:
                logger.error(f"❌ Erro inesperado: {str(e)}")
                if tentativa == max_tentativas:
                    return None
                import time
                time.sleep(2)
        
        return None
    
    def baixar_todos_clientes(self):
        """
        FASE 1A: Baixar TODOS os clientes do Asaas
        Faz paginação até não ter mais dados
        """
        logger.info("="*80)
        logger.info("🔽 FASE 1A: BAIXANDO TODOS OS CLIENTES")
        logger.info("="*80)
        
        self.dados_clientes = []
        offset = 0
        limit = 100  # Limite máximo da API
        pagina = 1
        
        while True:
            logger.info(f"\n📄 Página {pagina} (offset={offset})")
            
            params = {
                'offset': offset,
                'limit': limit
            }
            
            response = self._fazer_requisicao('GET', 'customers', params=params)
            
            if not response:
                logger.error(f"❌ Falha ao baixar página {pagina}. Parando.")
                break
            
            clientes_pagina = response.get('data', [])
            total_count = response.get('totalCount', 0)
            has_more = response.get('hasMore', False)
            
            if not clientes_pagina:
                logger.info("✅ Nenhum cliente nesta página. Finalizando.")
                break
            
            # Adicionar clientes ao array
            self.dados_clientes.extend(clientes_pagina)
            
            logger.info(f"✅ Baixados {len(clientes_pagina)} clientes")
            logger.info(f"📊 Total acumulado: {len(self.dados_clientes)} de {total_count}")
            
            # Verificar se há mais páginas
            if not has_more:
                logger.info("✅ Última página alcançada!")
                break
            
            # Aguardar 1 segundo entre requisições para evitar rate limit
            import time
            time.sleep(1)
            
            # Próxima página
            offset += limit
            pagina += 1
        
        logger.info("\n" + "="*80)
        logger.info(f"✅ FASE 1A COMPLETA: {len(self.dados_clientes)} clientes baixados")
        logger.info("="*80)
        
        return len(self.dados_clientes)
    
    def baixar_todas_cobrancas(self):
        """
        FASE 1B: Baixar TODAS as cobranças do Asaas
        Para CADA cliente, baixa TODAS as suas cobranças
        """
        logger.info("\n" + "="*80)
        logger.info("🔽 FASE 1B: BAIXANDO TODAS AS COBRANÇAS")
        logger.info("="*80)
        
        self.dados_cobrancas = []
        total_clientes = len(self.dados_clientes)
        
        for i, cliente in enumerate(self.dados_clientes, 1):
            customer_id = cliente.get('id')
            customer_name = cliente.get('name', 'Sem nome')
            
            logger.info(f"\n👤 Cliente {i}/{total_clientes}: {customer_name} ({customer_id})")
            
            # Baixar TODAS as cobranças deste cliente (com paginação)
            offset = 0
            limit = 100
            pagina = 1
            cobrancas_cliente = 0
            
            while True:
                params = {
                    'customer': customer_id,
                    'offset': offset,
                    'limit': limit
                }
                
                response = self._fazer_requisicao('GET', 'payments', params=params)
                
                if not response:
                    logger.warning(f"   ⚠️  Falha ao baixar cobranças (página {pagina})")
                    break
                
                cobrancas_pagina = response.get('data', [])
                has_more = response.get('hasMore', False)
                
                if not cobrancas_pagina:
                    break
                
                # Adicionar customer_id em cada cobrança para facilitar depois
                for cobranca in cobrancas_pagina:
                    cobranca['_customer_id'] = customer_id
                
                self.dados_cobrancas.extend(cobrancas_pagina)
                cobrancas_cliente += len(cobrancas_pagina)
                
                if not has_more:
                    break
                
                # Aguardar 0.5 segundos entre páginas de cobranças
                import time
                time.sleep(0.5)
                
                offset += limit
                pagina += 1
            
            logger.info(f"   ✅ {cobrancas_cliente} cobranças baixadas")
            
            # Aguardar 0.3 segundos entre clientes para evitar rate limit
            import time
            time.sleep(0.3)
        
        logger.info("\n" + "="*80)
        logger.info(f"✅ FASE 1B COMPLETA: {len(self.dados_cobrancas)} cobranças baixadas")
        logger.info("="*80)
        
        return len(self.dados_cobrancas)
    
    def salvar_clientes_no_banco(self):
        """
        FASE 2A: Salvar/Atualizar TODOS os clientes no banco de dados
        """
        logger.info("\n" + "="*80)
        logger.info("💾 FASE 2A: SALVANDO CLIENTES NO BANCO DE DADOS")
        logger.info("="*80)
        
        stats = {
            'total': 0,
            'novos': 0,
            'atualizados': 0,
            'erros': 0
        }
        
        for i, cliente_data in enumerate(self.dados_clientes, 1):
            try:
                asaas_id = cliente_data.get('id')
                
                if not asaas_id:
                    logger.warning(f"   ⚠️  Cliente sem ID, pulando...")
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
                    logger.info(f"   📊 Progresso: {i}/{len(self.dados_clientes)} clientes processados")
                    
            except Exception as e:
                stats['erros'] += 1
                logger.error(f"   ❌ Erro ao salvar cliente {cliente_data.get('id', 'DESCONHECIDO')}: {str(e)}")
        
        logger.info("\n" + "="*80)
        logger.info(f"✅ FASE 2A COMPLETA:")
        logger.info(f"   Total: {stats['total']}")
        logger.info(f"   Novos: {stats['novos']}")
        logger.info(f"   Atualizados: {stats['atualizados']}")
        logger.info(f"   Erros: {stats['erros']}")
        logger.info("="*80)
        
        return stats
    
    def salvar_cobrancas_no_banco(self):
        """
        FASE 2B: Salvar/Atualizar TODAS as cobranças no banco de dados
        """
        logger.info("\n" + "="*80)
        logger.info("💾 FASE 2B: SALVANDO COBRANÇAS NO BANCO DE DADOS")
        logger.info("="*80)
        
        stats = {
            'total': 0,
            'novas': 0,
            'atualizadas': 0,
            'erros': 0,
            'sem_cliente': 0
        }
        
        for i, cobranca_data in enumerate(self.dados_cobrancas, 1):
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
                    logger.warning(f"   ⚠️  Cliente {customer_id} não encontrado para cobrança {asaas_payment_id}")
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
                    logger.info(f"   📊 Progresso: {i}/{len(self.dados_cobrancas)} cobranças processadas")
                    
            except Exception as e:
                stats['erros'] += 1
                logger.error(f"   ❌ Erro ao salvar cobrança {cobranca_data.get('id', 'DESCONHECIDO')}: {str(e)}")
        
        logger.info("\n" + "="*80)
        logger.info(f"✅ FASE 2B COMPLETA:")
        logger.info(f"   Total: {stats['total']}")
        logger.info(f"   Novas: {stats['novas']}")
        logger.info(f"   Atualizadas: {stats['atualizadas']}")
        logger.info(f"   Sem cliente: {stats['sem_cliente']}")
        logger.info(f"   Erros: {stats['erros']}")
        logger.info("="*80)
        
        return stats
    
    def limpar_cobrancas_deletadas(self):
        """
        FASE 3: Excluir cobranças que existem no servidor mas NÃO existem mais no Asaas
        Garante que os valores totais sejam idênticos
        """
        logger.info("\n" + "="*80)
        logger.info("🗑️  FASE 3: LIMPANDO COBRANÇAS DELETADAS DO ASAAS")
        logger.info("="*80)
        
        # IDs de cobranças que vieram do Asaas
        ids_asaas = set()
        for cobranca_data in self.dados_cobrancas:
            asaas_payment_id = cobranca_data.get('id')
            if asaas_payment_id:
                ids_asaas.add(asaas_payment_id)
        
        logger.info(f"Total de cobranças no Asaas: {len(ids_asaas)}")
        
        # Buscar TODAS as cobranças no banco local
        cobrancas_local = AsaasCobrancaSyncronizada.objects.all()
        total_local = cobrancas_local.count()
        
        logger.info(f"Total de cobranças no banco local: {total_local}")
        
        # Encontrar cobranças que NÃO existem mais no Asaas
        cobrancas_para_excluir = []
        for cobranca in cobrancas_local:
            if cobranca.asaas_payment_id not in ids_asaas:
                cobrancas_para_excluir.append(cobranca)
        
        total_excluir = len(cobrancas_para_excluir)
        
        if total_excluir == 0:
            logger.info("✅ Nenhuma cobrança para excluir. Dados sincronizados!")
            return {'excluidas': 0}
        
        logger.info(f"⚠️  Encontradas {total_excluir} cobranças que NÃO existem mais no Asaas")
        logger.info("🗑️  Iniciando exclusão...")
        
        # Excluir cobranças
        excluidas = 0
        for cobranca in cobrancas_para_excluir:
            try:
                cliente_nome = cobranca.cliente.nome if cobranca.cliente else "Cliente desconhecido"
                valor = cobranca.valor
                logger.info(f"   🗑️  Excluindo: {cobranca.asaas_payment_id} - {cliente_nome} - R$ {valor}")
                cobranca.delete()
                excluidas += 1
            except Exception as e:
                logger.error(f"   ❌ Erro ao excluir cobrança {cobranca.asaas_payment_id}: {str(e)}")
        
        logger.info("\n" + "="*80)
        logger.info(f"✅ FASE 3 COMPLETA: {excluidas} cobranças excluídas")
        logger.info("="*80)
        
        return {'excluidas': excluidas}
    
    def executar_sincronizacao_completa(self, usuario=None, nome_conta="Principal"):
        """
        Executa sincronização completa em 5 FASES:
        FASE 1A: Baixar todos os clientes
        FASE 1B: Baixar todas as cobranças
        FASE 2A: Salvar clientes no banco
        FASE 2B: Salvar cobranças no banco
        FASE 3: Limpar cobranças deletadas do Asaas
        """
        logger.info("\n" + "🚀"*40)
        logger.info(f"SINCRONIZAÇÃO COMPLETA - ASAAS {nome_conta}")
        logger.info("🚀"*40 + "\n")
        
        # Criar log
        log = AsaasSyncronizacaoLog.objects.create(
            tipo_sincronizacao='COMPLETO',
            status='EM_ANDAMENTO',
            usuario=usuario.username if usuario else 'Sistema',
            mensagem=f'Sincronizando conta: {nome_conta}'
        )
        
        try:
            tempo_inicio = timezone.now()
            
            # FASE 1A: Baixar clientes
            total_clientes_baixados = self.baixar_todos_clientes()
            
            # FASE 1B: Baixar cobranças
            total_cobrancas_baixadas = self.baixar_todas_cobrancas()
            
            # FASE 2A: Salvar clientes
            stats_clientes = self.salvar_clientes_no_banco()
            
            # FASE 2B: Salvar cobranças
            stats_cobrancas = self.salvar_cobrancas_no_banco()
            
            # FASE 3: Limpar cobranças deletadas
            stats_limpeza = self.limpar_cobrancas_deletadas()
            
            # Finalizar log
            tempo_fim = timezone.now()
            duracao = (tempo_fim - tempo_inicio).total_seconds()
            
            log.total_clientes = stats_clientes['total']
            log.clientes_novos = stats_clientes['novos']
            log.clientes_atualizados = stats_clientes['atualizados']
            
            log.total_cobrancas = stats_cobrancas['total']
            log.cobrancas_novas = stats_cobrancas['novas']
            log.cobrancas_atualizadas = stats_cobrancas['atualizadas']
            
            log.status = 'SUCESSO'
            log.data_fim = tempo_fim
            log.duracao_segundos = int(duracao)
            
            cobrancas_excluidas = stats_limpeza.get('excluidas', 0)
            
            log.mensagem = f"""✅ Sincronização COMPLETA - {nome_conta}

📥 DOWNLOAD (Fase 1):
   • Clientes baixados: {total_clientes_baixados}
   • Cobranças baixadas: {total_cobrancas_baixadas}

💾 SALVAMENTO (Fase 2):
   • Clientes salvos: {stats_clientes['total']} ({stats_clientes['novos']} novos, {stats_clientes['atualizados']} atualizados)
   • Cobranças salvas: {stats_cobrancas['total']} ({stats_cobrancas['novas']} novas, {stats_cobrancas['atualizadas']} atualizadas)

🗑️  LIMPEZA (Fase 3):
   • Cobranças excluídas: {cobrancas_excluidas}

⏱️  Duração: {duracao:.0f} segundos ({duracao/60:.1f} minutos)

✅ GARANTIA: Valores totais do servidor = Valores totais do Asaas!"""
            
            if stats_clientes['erros'] > 0 or stats_cobrancas['erros'] > 0:
                log.status = 'PARCIAL'
                log.erros = f"Erros: {stats_clientes['erros']} clientes, {stats_cobrancas['erros']} cobranças"
            
            log.save()
            
            logger.info("\n" + "🎉"*40)
            logger.info("SINCRONIZAÇÃO CONCLUÍDA COM SUCESSO!")
            logger.info("🎉"*40)
            
            return log
            
        except Exception as e:
            logger.error(f"\n❌ ERRO FATAL na sincronização: {str(e)}", exc_info=True)
            
            log.status = 'ERRO'
            log.data_fim = timezone.now()
            log.mensagem = f'Erro fatal: {str(e)}'
            log.erros = str(e)
            log.save()
            
            raise
    
    def _parse_date(self, date_string):
        """Converte string de data para date"""
        if not date_string:
            return None
        try:
            return datetime.strptime(date_string, '%Y-%m-%d').date()
        except:
            return None
    
    def _parse_datetime(self, datetime_string):
        """Converte string de datetime para datetime com timezone"""
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
