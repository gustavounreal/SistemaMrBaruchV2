"""
Serviço de sincronização com Asaas
Baixa todos os clientes e cobranças
"""
import requests
import logging
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from datetime import datetime
from .models import AsaasClienteSyncronizado, AsaasCobrancaSyncronizada, AsaasSyncronizacaoLog

logger = logging.getLogger(__name__)


class AsaasSyncService:
    """Serviço para sincronizar dados do Asaas"""
    
    def __init__(self):
        # PRODUÇÃO: Sempre usa a URL de produção do ASAAS
        self.base_url = getattr(settings, 'ASAAS_API_URL', 'https://api.asaas.com/v3')
        self.api_token = getattr(settings, 'ASAAS_API_TOKEN', '')
        self.headers = {
            'Content-Type': 'application/json',
            'access_token': self.api_token
        }
        # Timeout de 120 segundos por requisição (tempo razoável para API externa)
        # O processo completo pode demorar mais, mas cada requisição individual deve ser rápida
        self.timeout = 120
        self.limite_por_pagina = 100 
    
    def _fazer_requisicao(self, metodo, endpoint, params=None):
        """Faz requisição à API do Asaas"""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = requests.request(
                method=metodo,
                url=url,
                params=params,
                headers=self.headers,
                timeout=self.timeout
            )
            
            # Log detalhado para debug
            logger.info(f"Requisição {metodo} para {url}")
            logger.info(f"Status Code: {response.status_code}")
            logger.info(f"Headers enviados: {self.headers}")
            
            # Verificar status code ANTES de tentar parsear JSON
            if response.status_code == 401:
                logger.error("❌ ERRO 401: Token de acesso inválido ou expirado")
                logger.error(f"Token usado: {self.api_token[:10]}...")
                return None
            elif response.status_code == 403:
                logger.error("❌ ERRO 403: Sem permissão para acessar este recurso")
                return None
            elif response.status_code == 404:
                logger.error(f"❌ ERRO 404: Endpoint não encontrado: {endpoint}")
                logger.error(f"URL completa: {url}")
                logger.error(f"Resposta: {response.text[:500]}")
                return None
            elif response.status_code != 200:
                logger.error(f"❌ Erro Asaas {response.status_code}: {response.text[:500]}")
                return None
            
            # Somente tenta parsear JSON se status 200
            if response.status_code == 200:
                try:
                    return response.json()
                except ValueError as json_error:
                    logger.error(f"❌ Resposta não é JSON válido. Conteúdo: {response.text[:500]}")
                    logger.error(f"Erro de parse: {str(json_error)}")
                    return None
                
        except requests.exceptions.Timeout:
            logger.error(f"❌ Timeout ao conectar com ASAAS (>{self.timeout}s)")
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ Erro de conexão com ASAAS: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ Erro inesperado na requisição: {str(e)}")
            return None
    
    def sincronizar_clientes(self, limit=100, offset=0):
        """
        Sincroniza clientes do Asaas
        
        Args:
            limit: Quantidade de registros por página (max 100)
            offset: Offset para paginação
            
        Returns:
            dict com estatísticas
        """
        logger.info(f"Iniciando sincronização de clientes (offset={offset}, limit={limit})")
        
        stats = {
            'total': 0,
            'novos': 0,
            'atualizados': 0,
            'erros': 0
        }
        
        params = {
            'offset': offset,
            'limit': limit
        }
        
        response = self._fazer_requisicao('GET', 'customers', params=params)
        
        if not response:
            logger.error("Falha ao buscar clientes do Asaas")
            return stats
        
        clientes = response.get('data', [])
        total_count = response.get('totalCount', 0)
        has_more = response.get('hasMore', False)
        
        logger.info(f"Encontrados {len(clientes)} clientes (total: {total_count})")
        
        for cliente_data in clientes:
            try:
                asaas_id = cliente_data.get('id')
                
                # Verifica se cliente já existe
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
                    logger.info(f"✅ Cliente novo: {cliente.nome}")
                else:
                    stats['atualizados'] += 1
                    logger.info(f"🔄 Cliente atualizado: {cliente.nome}")
                    
            except Exception as e:
                stats['erros'] += 1
                logger.error(f"Erro ao sincronizar cliente {cliente_data.get('id')}: {str(e)}")
        
        # NÃO fazer paginação recursiva automática para evitar timeout
        # A sincronização deve ser feita em lotes controlados
        if has_more:
            logger.info(f"⚠️  Há mais {total_count - len(clientes)} clientes disponíveis. Use a sincronização de boletos faltantes para continuar.")
        
        return stats
    
    def sincronizar_cobrancas_cliente(self, cliente_sync, limit=100, offset=0):
        """
        Sincroniza cobranças de um cliente específico
        
        Args:
            cliente_sync: Instância de AsaasClienteSyncronizado
            limit: Quantidade de registros por página
            offset: Offset para paginação
            
        Returns:
            dict com estatísticas
        """
        stats = {
            'total': 0,
            'novas': 0,
            'atualizadas': 0,
            'erros': 0
        }
        
        params = {
            'customer': cliente_sync.asaas_customer_id,
            'offset': offset,
            'limit': limit
        }
        
        response = self._fazer_requisicao('GET', 'payments', params=params)
        
        if not response:
            return stats
        
        cobrancas = response.get('data', [])
        has_more = response.get('hasMore', False)
        
        for cobranca_data in cobrancas:
            try:
                asaas_payment_id = cobranca_data.get('id')
                
                cobranca, created = AsaasCobrancaSyncronizada.objects.update_or_create(
                    asaas_payment_id=asaas_payment_id,
                    defaults={
                        'cliente': cliente_sync,
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
                    
            except Exception as e:
                stats['erros'] += 1
                logger.error(f"Erro ao sincronizar cobrança {cobranca_data.get('id')}: {str(e)}")
        
        # NÃO fazer paginação recursiva - processar apenas primeira página
        # Para sincronizar todas as cobranças, use sincronizar_boletos_faltantes
        if has_more:
            logger.info(f"   ⚠️  Cliente tem mais cobranças. Processando apenas primeira página para evitar timeout.")
        
        return stats
    
    def sincronizar_todas_cobrancas(self, limite_clientes=None):
        """
        Sincroniza cobranças de todos os clientes
        
        Args:
            limite_clientes: Limita quantos clientes processar (None = todos)
        """
        logger.info("Iniciando sincronização de cobranças de todos os clientes")
        
        stats_total = {
            'total': 0,
            'novas': 0,
            'atualizadas': 0,
            'erros': 0,
            'clientes_processados': 0
        }
        
        clientes = AsaasClienteSyncronizado.objects.all()
        
        # Limitar quantidade de clientes se especificado
        if limite_clientes:
            clientes = clientes[:limite_clientes]
            logger.info(f"Limitando processamento a {limite_clientes} clientes")
        
        total_clientes = clientes.count()
        logger.info(f"Total de clientes a processar: {total_clientes}")
        
        for i, cliente in enumerate(clientes, 1):
            logger.info(f"Processando cliente {i}/{total_clientes}: {cliente.nome}")
            
            try:
                stats_cliente = self.sincronizar_cobrancas_cliente(cliente)
                
                stats_total['total'] += stats_cliente['total']
                stats_total['novas'] += stats_cliente['novas']
                stats_total['atualizadas'] += stats_cliente['atualizadas']
                stats_total['erros'] += stats_cliente['erros']
                stats_total['clientes_processados'] += 1
                
                logger.info(f"Cliente {cliente.nome}: {stats_cliente['total']} cobranças ({stats_cliente['novas']} novas)")
            except Exception as e:
                logger.error(f"Erro ao processar cliente {cliente.nome}: {e}")
                stats_total['erros'] += 1
        
        return stats_total
    
    def sincronizar_tudo(self, usuario=None, limite_clientes=None):
        """
        Sincroniza clientes e cobranças
        Cria log da sincronização
        
        Args:
            usuario: Usuário que iniciou a sincronização
            limite_clientes: Quantos clientes processar cobranças (None = TODOS)
            
        Returns:
            AsaasSyncronizacaoLog
        """
        logger.info("="*60)
        logger.info("INICIANDO SINCRONIZAÇÃO COMPLETA DO ASAAS")
        if limite_clientes:
            logger.info(f"Limite de clientes para cobranças: {limite_clientes}")
        else:
            logger.info("Processando TODOS os clientes para cobranças")
        logger.info("="*60)
        
        # Criar log
        log = AsaasSyncronizacaoLog.objects.create(
            status='SUCESSO',
            usuario=usuario.username if usuario else 'Sistema'
        )
        
        try:
            # 1. Sincronizar clientes (SEM paginação recursiva - apenas primeira página)
            logger.info("\n📋 ETAPA 1: Sincronizando primeiros 100 clientes...")
            stats_clientes = self.sincronizar_clientes(limit=100, offset=0)
            
            log.total_clientes = stats_clientes['total']
            log.clientes_novos = stats_clientes['novos']
            log.clientes_atualizados = stats_clientes['atualizados']
            
            logger.info(f"✅ Clientes: {stats_clientes['total']} processados, {stats_clientes['novos']} novos, {stats_clientes['atualizados']} atualizados")
            
            # 2. Sincronizar cobranças apenas dos primeiros clientes
            # Limitar para evitar timeout
            limite_cobrancas = limite_clientes if limite_clientes else 10
            logger.info(f"\n💰 ETAPA 2: Sincronizando cobranças dos primeiros {limite_cobrancas} clientes...")
            
            stats_cobrancas = self.sincronizar_todas_cobrancas(limite_clientes=limite_cobrancas)
            
            log.total_cobrancas = stats_cobrancas['total']
            log.cobrancas_novas = stats_cobrancas['novas']
            log.cobrancas_atualizadas = stats_cobrancas['atualizadas']
            
            logger.info(f"✅ Cobranças: {stats_cobrancas['total']} total, {stats_cobrancas['novas']} novas, {stats_cobrancas['atualizadas']} atualizadas")
            
            # Finalizar log
            log.data_fim = timezone.now()
            log.calcular_duracao()
            log.mensagem = f"""Sincronização RÁPIDA concluída com sucesso!

📋 Clientes: {stats_clientes['total']} processados ({stats_clientes['novos']} novos)
💰 Cobranças: {stats_cobrancas['total']} processadas ({stats_cobrancas['novas']} novas)

⚠️  ATENÇÃO: Esta é uma sincronização rápida (primeiros 100 clientes e 10 primeiros para cobranças).
Para sincronizar TODOS os dados, use: "Sincronizar Boletos Faltantes" """
            
            if stats_clientes['erros'] > 0 or stats_cobrancas['erros'] > 0:
                log.status = 'PARCIAL'
                log.erros = f"Erros: {stats_clientes['erros']} clientes, {stats_cobrancas['erros']} cobranças"
            
            log.save()
            
            logger.info("="*60)
            logger.info("✅ SINCRONIZAÇÃO CONCLUÍDA COM SUCESSO!")
            logger.info(f"⏱️  Duração: {log.duracao_segundos}s")
            logger.info("="*60)
            
            return log
            
        except Exception as e:
            logger.error(f"❌ ERRO na sincronização: {str(e)}", exc_info=True)
            
            log.status = 'ERRO'
            log.data_fim = timezone.now()
            log.calcular_duracao()
            log.erros = str(e)
            log.mensagem = f"Erro durante a sincronização: {str(e)}"
            log.save()
            
            return log
    
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
            # Formato: 2023-01-15T10:30:00.000-03:00 ou 2023-01-15
            if 'T' in datetime_string:
                dt = datetime.fromisoformat(datetime_string.replace('Z', '+00:00'))
            else:
                # Se for apenas data (2023-01-15), converte para datetime com timezone
                dt = datetime.strptime(datetime_string, '%Y-%m-%d')
            
            # Garante que tem timezone
            if dt.tzinfo is None:
                from django.utils import timezone as tz
                dt = tz.make_aware(dt)
            
            return dt
        except Exception as e:
            logger.warning(f"Erro ao parsear datetime '{datetime_string}': {e}")
            return None

    def sincronizar_boletos_faltantes(self, usuario=None):
        """
        Sincroniza apenas os boletos faltantes dos clientes já cadastrados.
        Ideal para executar após uma sincronização que foi interrompida ou limitada.
        
        Estratégia:
        1. Busca todos os clientes no banco local
        2. Para cada cliente, busca cobranças na API
        3. Compara com banco local e adiciona apenas as faltantes
        
        Args:
            usuario: Usuário que iniciou a sincronização
            
        Returns:
            dict com estatísticas
        """
        logger.info("="*60)
        logger.info("SINCRONIZANDO BOLETOS FALTANTES")
        logger.info("="*60)
        
        stats = {
            'clientes_processados': 0,
            'clientes_sem_cobrancas': 0,
            'total_cobrancas_api': 0,
            'cobrancas_novas': 0,
            'cobrancas_atualizadas': 0,
            'erros': 0
        }
        
        # Buscar todos os clientes do banco local
        clientes = AsaasClienteSyncronizado.objects.all()
        total_clientes = clientes.count()
        
        logger.info(f"Total de clientes no banco local: {total_clientes}")
        
        for i, cliente in enumerate(clientes, 1):
            try:
                logger.info(f"\n[{i}/{total_clientes}] Processando: {cliente.nome}")
                
                # Contar cobranças já cadastradas
                cobrancas_locais = AsaasCobrancaSyncronizada.objects.filter(cliente=cliente).count()
                logger.info(f"  Cobranças locais: {cobrancas_locais}")
                
                # Buscar cobranças da API
                offset = 0
                limit = 100
                cobrancas_api_count = 0
                novas_count = 0
                atualizadas_count = 0
                
                while True:
                    params = {
                        'customer': cliente.asaas_customer_id,
                        'offset': offset,
                        'limit': limit
                    }
                    
                    response = self._fazer_requisicao('GET', 'payments', params=params)
                    
                    if not response:
                        logger.warning(f"  ⚠️ Falha ao buscar cobranças da API")
                        break
                    
                    cobrancas_data = response.get('data', [])
                    has_more = response.get('hasMore', False)
                    
                    cobrancas_api_count += len(cobrancas_data)
                    
                    # Processar cada cobrança
                    for cobranca_data in cobrancas_data:
                        try:
                            asaas_payment_id = cobranca_data.get('id')
                            
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
                            
                            if created:
                                novas_count += 1
                            else:
                                atualizadas_count += 1
                                
                        except Exception as e:
                            logger.error(f"    ❌ Erro ao processar cobrança {cobranca_data.get('id')}: {str(e)}")
                            stats['erros'] += 1
                    
                    if not has_more:
                        break
                    
                    offset += limit
                
                # Estatísticas do cliente
                logger.info(f"  Cobranças na API: {cobrancas_api_count}")
                logger.info(f"  ✅ Novas: {novas_count} | 🔄 Atualizadas: {atualizadas_count}")
                
                stats['clientes_processados'] += 1
                stats['total_cobrancas_api'] += cobrancas_api_count
                stats['cobrancas_novas'] += novas_count
                stats['cobrancas_atualizadas'] += atualizadas_count
                
                if cobrancas_api_count == 0:
                    stats['clientes_sem_cobrancas'] += 1
                
            except Exception as e:
                logger.error(f"  ❌ Erro ao processar cliente {cliente.nome}: {str(e)}")
                stats['erros'] += 1
        
        logger.info("\n" + "="*60)
        logger.info("RESUMO DA SINCRONIZAÇÃO DE BOLETOS FALTANTES")
        logger.info("="*60)
        logger.info(f"Clientes processados: {stats['clientes_processados']}")
        logger.info(f"Clientes sem cobranças: {stats['clientes_sem_cobrancas']}")
        logger.info(f"Total de cobranças na API: {stats['total_cobrancas_api']}")
        logger.info(f"✅ Cobranças NOVAS baixadas: {stats['cobrancas_novas']}")
        logger.info(f"🔄 Cobranças ATUALIZADAS: {stats['cobrancas_atualizadas']}")
        logger.info(f"❌ Erros: {stats['erros']}")
        logger.info("="*60)
        
        return stats
