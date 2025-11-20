"""
Gerenciador de Webhooks do Asaas
Responsável por listar e reenviar webhooks pendentes
"""
import requests
import time
import logging
from typing import List, Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class AsaasWebhookManager:
    """
    Gerencia webhooks do Asaas: listagem, reenvio e monitoramento
    """
    
    def __init__(self, api_token: str = None):
        """
        Inicializa o gerenciador com o token da API
        
        Args:
            api_token: Token de acesso da API Asaas (usa settings se não fornecido)
        """
        self.api_token = api_token or getattr(settings, 'ASAAS_API_TOKEN', '')
        
        # FORÇAR SEMPRE PRODUÇÃO
        self.base_url = 'https://api.asaas.com/v3'  # SEMPRE PRODUÇÃO
        
        self.headers = {
            'access_token': self.api_token,
            'Content-Type': 'application/json',
            'User-Agent': 'MrBaruch-System/1.0'
        }
        
        self.timeout = 30
        self.delay_between_requests = 0.5  # 500ms entre requisições
    
    def list_webhooks(
        self, 
        status: str = 'PENDING', 
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Lista webhooks com filtros
        
        Args:
            status: Status dos webhooks (PENDING, SENT, ERROR)
            limit: Limite de resultados
            offset: Offset para paginação
            
        Returns:
            Dict com dados dos webhooks e metadados
        """
        try:
            url = f"{self.base_url}/webhooks"
            params = {
                'status': status,
                'limit': limit,
                'offset': offset
            }
            
            logger.info(f"Listando webhooks com status {status}, limit {limit}, offset {offset}")
            
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"Webhooks encontrados: {len(data.get('data', []))}")
            
            return {
                'success': True,
                'data': data.get('data', []),
                'hasMore': data.get('hasMore', False),
                'totalCount': data.get('totalCount', 0),
                'limit': limit,
                'offset': offset
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao listar webhooks: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'data': [],
                'hasMore': False,
                'totalCount': 0
            }
    
    def resend_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """
        Reenvia um webhook específico
        
        Args:
            webhook_id: ID do webhook a ser reenviado
            
        Returns:
            Dict com resultado do reenvio
        """
        try:
            url = f"{self.base_url}/webhooks/{webhook_id}/resend"
            
            logger.info(f"Reenviando webhook: {webhook_id}")
            
            response = requests.post(
                url,
                headers=self.headers,
                timeout=self.timeout
            )
            
            success = response.status_code in [200, 201, 202, 204]
            
            result = {
                'success': success,
                'status_code': response.status_code,
                'webhook_id': webhook_id
            }
            
            try:
                result['data'] = response.json()
            except:
                result['data'] = None
            
            if success:
                logger.info(f"Webhook {webhook_id} reenviado com sucesso")
            else:
                logger.warning(f"Falha ao reenviar webhook {webhook_id}: HTTP {response.status_code}")
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao reenviar webhook {webhook_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'webhook_id': webhook_id
            }
    
    def resend_all_pending(self, max_webhooks: int = 100) -> Dict[str, Any]:
        """
        Busca e reenvia todos os webhooks pendentes
        
        Args:
            max_webhooks: Número máximo de webhooks a processar
            
        Returns:
            Dict com resumo do processamento
        """
        logger.info("Iniciando reenvio de webhooks pendentes...")
        
        # Buscar webhooks pendentes
        webhooks_response = self.list_webhooks(status='PENDING', limit=max_webhooks)
        
        if not webhooks_response['success']:
            return {
                'success': False,
                'error': webhooks_response.get('error', 'Erro ao listar webhooks'),
                'processed': 0,
                'succeeded': 0,
                'failed': 0,
                'results': []
            }
        
        pending_webhooks = webhooks_response['data']
        total_count = webhooks_response.get('totalCount', len(pending_webhooks))
        
        logger.info(f"Encontrados {len(pending_webhooks)} webhooks pendentes (total: {total_count})")
        
        if not pending_webhooks:
            return {
                'success': True,
                'message': 'Nenhum webhook pendente encontrado',
                'processed': 0,
                'succeeded': 0,
                'failed': 0,
                'results': [],
                'total_pending': 0
            }
        
        # Processar cada webhook
        results = []
        succeeded = 0
        failed = 0
        
        for idx, webhook in enumerate(pending_webhooks, 1):
            webhook_id = webhook.get('id')
            event = webhook.get('event', 'unknown')
            
            logger.info(f"Processando {idx}/{len(pending_webhooks)}: {webhook_id} - {event}")
            
            # Reenviar webhook
            result = self.resend_webhook(webhook_id)
            
            result['event'] = event
            result['created'] = webhook.get('created')
            result['url'] = webhook.get('url')
            
            results.append(result)
            
            if result['success']:
                succeeded += 1
            else:
                failed += 1
            
            # Delay para não sobrecarregar a API
            if idx < len(pending_webhooks):
                time.sleep(self.delay_between_requests)
        
        summary = {
            'success': True,
            'processed': len(results),
            'succeeded': succeeded,
            'failed': failed,
            'total_pending': total_count,
            'has_more': webhooks_response.get('hasMore', False),
            'results': results
        }
        
        logger.info(
            f"Reenvio concluído: {succeeded}/{len(results)} webhooks "
            f"reenviados com sucesso"
        )
        
        return summary
    
    def get_webhook_details(self, webhook_id: str) -> Dict[str, Any]:
        """
        Obtém detalhes de um webhook específico
        
        Args:
            webhook_id: ID do webhook
            
        Returns:
            Dict com detalhes do webhook e status
        """
        try:
            url = f"{self.base_url}/webhooks/{webhook_id}"
            
            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            webhook_data = response.json()
            
            return {
                'status': 'success',
                'success': True,
                'data': webhook_data,
                'webhook_url': webhook_data.get('url'),
                'enabled': webhook_data.get('enabled'),
                'interrupted': webhook_data.get('interrupted')
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao obter detalhes do webhook {webhook_id}: {str(e)}")
            return {
                'status': 'error',
                'success': False,
                'error': str(e)
            }
    
    def list_webhook_events(self) -> List[str]:
        """
        Lista todos os tipos de eventos de webhook disponíveis
        
        Returns:
            Lista de eventos
        """
        return [
            'PAYMENT_CREATED',
            'PAYMENT_UPDATED',
            'PAYMENT_CONFIRMED',
            'PAYMENT_RECEIVED',
            'PAYMENT_OVERDUE',
            'PAYMENT_DELETED',
            'PAYMENT_RESTORED',
            'PAYMENT_REFUNDED',
            'PAYMENT_RECEIVED_IN_CASH_UNDONE',
            'PAYMENT_CHARGEBACK_REQUESTED',
            'PAYMENT_CHARGEBACK_DISPUTE',
            'PAYMENT_AWAITING_CHARGEBACK_REVERSAL',
            'PAYMENT_DUNNING_RECEIVED',
            'PAYMENT_DUNNING_REQUESTED',
            'PAYMENT_BANK_SLIP_VIEWED',
            'PAYMENT_CHECKOUT_VIEWED'
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Obtém estatísticas dos webhooks
        
        Returns:
            Dict com estatísticas
        """
        stats = {
            'pending': 0,
            'sent': 0,
            'error': 0,
            'total': 0
        }
        
        try:
            # Buscar cada status
            for status in ['PENDING', 'SENT', 'ERROR']:
                response = self.list_webhooks(status=status, limit=1)
                if response['success']:
                    count = response.get('totalCount', 0)
                    stats[status.lower()] = count
                    stats['total'] += count
            
            stats['success'] = True
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {str(e)}")
            stats['success'] = False
            stats['error'] = str(e)
        
        return stats
