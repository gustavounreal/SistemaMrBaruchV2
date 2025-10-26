import json
import logging
from django.utils import timezone
from .models import LogSistema
from .services import LogService, NotificacaoService

logger = logging.getLogger(__name__)

class AsaasWebhookHandler:
    """
    Handler para processar webhooks do ASAAS
    """
    
    @staticmethod
    def processar_webhook_pagamento(dados_webhook):
        """
        Processa webhook de atualização de pagamento
        """
        try:
            payment = dados_webhook.get('payment', {})
            payment_id = payment.get('id')
            status = payment.get('status')
            event = dados_webhook.get('event')
            
            LogService.registrar(
                nivel='INFO',
                mensagem=f"Webhook ASAAS: {event} - Payment: {payment_id} - Status: {status}",
                modulo='core',
                acao='asaas_webhook'
            )
            
            # Aqui você implementaria a lógica específica para cada tipo de evento
            if event == 'PAYMENT_RECEIVED':
                return AsaasWebhookHandler._processar_pagamento_recebido(payment)
            elif event == 'PAYMENT_OVERDUE':
                return AsaasWebhookHandler._processar_pagamento_vencido(payment)
            elif event == 'PAYMENT_DELETED':
                return AsaasWebhookHandler._processar_pagamento_excluido(payment)
                
            return True
            
        except Exception as e:
            logger.error(f"Erro ao processar webhook ASAAS: {str(e)}")
            LogService.registrar(
                nivel='ERROR',
                mensagem=f"Erro no webhook ASAAS: {str(e)}",
                modulo='core',
                acao='asaas_webhook_error'
            )
            return False
    
    @staticmethod
    def _processar_pagamento_recebido(payment):
        """Processa pagamento confirmado"""
        payment_id = payment.get('id')
        value = payment.get('value')
        
        # Atualizar status do PIX Levantamento
        from financeiro.models import PixLevantamento
        try:
            pix_levantamento = PixLevantamento.objects.get(asaas_payment_id=payment_id)
            pix_levantamento.status_pagamento = 'pago'
            pix_levantamento.save(update_fields=['status_pagamento'])
            
            # Atualizar status do Lead para LEVANTAMENTO_PAGO
            if pix_levantamento.lead:
                pix_levantamento.lead.status = 'LEVANTAMENTO_PAGO'
                pix_levantamento.lead.save(update_fields=['status'])
            
            LogService.registrar(
                nivel='INFO',
                mensagem=f"Pagamento confirmado e PIX Levantamento atualizado: {payment_id} - R$ {value}",
                modulo='financeiro',
                acao='pagamento_confirmado'
            )
        except PixLevantamento.DoesNotExist:
            LogService.registrar(
                nivel='WARNING',
                mensagem=f"PIX Levantamento não encontrado para payment_id: {payment_id}",
                modulo='financeiro',
                acao='pagamento_confirmado_sem_registro'
            )
        
        return True
    
    @staticmethod
    def _processar_pagamento_vencido(payment):
        """Processa pagamento vencido"""
        payment_id = payment.get('id')
        
        # Atualizar status do PIX Levantamento para vencido
        from financeiro.models import PixLevantamento
        try:
            pix_levantamento = PixLevantamento.objects.get(asaas_payment_id=payment_id)
            pix_levantamento.status_pagamento = 'vencido'
            pix_levantamento.save(update_fields=['status_pagamento'])
            
            # Atualizar status do Lead para LEVANTAMENTO_VENCIDO
            if pix_levantamento.lead:
                pix_levantamento.lead.status = 'LEVANTAMENTO_VENCIDO'
                pix_levantamento.lead.save(update_fields=['status'])
            
            LogService.registrar(
                nivel='WARNING',
                mensagem=f"Pagamento vencido e PIX Levantamento atualizado: {payment_id}",
                modulo='financeiro',
                acao='pagamento_vencido'
            )
        except PixLevantamento.DoesNotExist:
            LogService.registrar(
                nivel='WARNING',
                mensagem=f"PIX Levantamento não encontrado para payment_id vencido: {payment_id}",
                modulo='financeiro',
                acao='pagamento_vencido_sem_registro'
            )
        
        return True
    
    @staticmethod
    def _processar_pagamento_excluido(payment):
        """Processa pagamento excluído"""
        payment_id = payment.get('id')
        
        LogService.registrar(
            nivel='INFO',
            mensagem=f"Pagamento excluído: {payment_id}",
            modulo='financeiro',
            acao='pagamento_excluido'
        )
        
        return True

# Instância global do handler
webhook_handler = AsaasWebhookHandler()