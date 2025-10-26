"""
Signals para criação automática de comissões.

Garante que comissões sejam criadas imediatamente quando:
- PIX de levantamento é pago
- Entrada de venda é paga
- Parcela é paga
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from financeiro.models import PixLevantamento, Parcela
from vendas.models import Venda

logger = logging.getLogger(__name__)


@receiver(post_save, sender=PixLevantamento)
def criar_comissao_pix_levantamento(sender, instance, created, **kwargs):
    """
    Cria comissão de atendente quando PIX de levantamento é marcado como pago.
    """
    if instance.status_pagamento == 'pago':
        from comissoes.models import ComissaoLead
        from core.commission_service import CommissionService
        
        # Verificar se já existe comissão
        if not ComissaoLead.objects.filter(lead=instance.lead).exists():
            try:
                comissao = CommissionService.criar_comissao_atendente(instance.lead)
                if comissao:
                    logger.info(f"[Signal] ✅ Comissão atendente criada automaticamente: Lead #{instance.lead.id}")
            except Exception as e:
                logger.error(f"[Signal] ❌ Erro ao criar comissão atendente: {e}")


@receiver(post_save, sender=Venda)
def criar_comissao_entrada_venda(sender, instance, created, **kwargs):
    """
    Cria comissões de entrada (captador + consultor) quando entrada é marcada como PAGA.
    """
    if instance.status_pagamento_entrada == 'PAGO' and instance.valor_entrada > 0:
        from financeiro.models import Comissao
        from core.commission_service import CommissionService
        
        # Verificar se já existem comissões de entrada
        tem_comissao = Comissao.objects.filter(
            venda=instance,
            tipo_comissao__in=['CAPTADOR_ENTRADA', 'CONSULTOR_ENTRADA']
        ).exists()
        
        if not tem_comissao:
            try:
                comissoes = CommissionService.criar_comissao_entrada_venda(instance)
                if comissoes.get('captador'):
                    logger.info(f"[Signal] ✅ Comissão CAPTADOR_ENTRADA criada automaticamente: Venda #{instance.id}")
                if comissoes.get('consultor'):
                    logger.info(f"[Signal] ✅ Comissão CONSULTOR_ENTRADA criada automaticamente: Venda #{instance.id}")
            except Exception as e:
                logger.error(f"[Signal] ❌ Erro ao criar comissões entrada: {e}")


@receiver(post_save, sender=Parcela)
def criar_comissao_parcela_paga(sender, instance, created, **kwargs):
    """
    Cria comissões (captador + consultor) quando parcela é marcada como paga.
    
    Se for parcela 0 (entrada via BOLETO), cria comissão de ENTRADA.
    Se for parcela > 0, cria comissão de PARCELA.
    """
    if instance.status == 'paga':
        from financeiro.models import Comissao
        from core.commission_service import CommissionService
        from vendas.models import Venda
        
        # Se for entrada (numero_parcela = 0), tratar como entrada
        if instance.numero_parcela == 0:
            # Atualizar status_pagamento_entrada da venda
            try:
                venda = instance.venda
                if venda.status_pagamento_entrada != 'PAGO':
                    venda.status_pagamento_entrada = 'PAGO'
                    venda.save(update_fields=['status_pagamento_entrada'])
                    logger.info(f"[Signal] ✅ Venda #{venda.id} marcada com entrada PAGA")
            except Exception as e:
                logger.error(f"[Signal] ❌ Erro ao atualizar status_pagamento_entrada: {e}")
            
            # Verificar se já existem comissões de entrada
            tem_comissao = Comissao.objects.filter(
                venda=instance.venda,
                tipo_comissao__in=['CAPTADOR_ENTRADA', 'CONSULTOR_ENTRADA']
            ).exists()
            
            if not tem_comissao:
                try:
                    comissoes = CommissionService.criar_comissao_entrada_venda(instance.venda)
                    if comissoes.get('captador'):
                        logger.info(f"[Signal] ✅ Comissão CAPTADOR_ENTRADA (BOLETO) criada: Venda #{instance.venda.id}")
                    if comissoes.get('consultor'):
                        logger.info(f"[Signal] ✅ Comissão CONSULTOR_ENTRADA (BOLETO) criada: Venda #{instance.venda.id}")
                except Exception as e:
                    logger.error(f"[Signal] ❌ Erro ao criar comissões entrada (BOLETO): {e}")
        
        else:
            # Parcela normal (não é entrada)
            # Verificar se já existem comissões desta parcela
            tem_comissao = Comissao.objects.filter(
                venda=instance.venda,
                parcela=instance,
                tipo_comissao__in=['CAPTADOR_PARCELA', 'CONSULTOR_PARCELA']
            ).exists()
            
            if not tem_comissao:
                try:
                    comissoes = CommissionService.criar_comissao_parcela_paga(instance)
                    if comissoes.get('captador'):
                        logger.info(f"[Signal] ✅ Comissão CAPTADOR_PARCELA criada automaticamente: Parcela #{instance.id}")
                    if comissoes.get('consultor'):
                        logger.info(f"[Signal] ✅ Comissão CONSULTOR_PARCELA criada automaticamente: Parcela #{instance.id}")
                except Exception as e:
                    logger.error(f"[Signal] ❌ Erro ao criar comissões parcela: {e}")
