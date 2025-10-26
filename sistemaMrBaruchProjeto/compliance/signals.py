# compliance/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from financeiro.models import PixLevantamento
from .models import AnaliseCompliance, StatusAnaliseCompliance


@receiver(post_save, sender=PixLevantamento)
def criar_analise_compliance_apos_pagamento(sender, instance, created, **kwargs):
    """
    Quando um PIX de levantamento é pago, cria automaticamente
    uma análise de compliance para o lead e atualiza seu status.
    """
    # Verifica se o status mudou para 'pago'
    if instance.status_pagamento == 'pago' and instance.lead:
        # Verifica se já existe análise para este lead
        analise_existente = AnaliseCompliance.objects.filter(
            lead=instance.lead,
            status__in=[
                StatusAnaliseCompliance.AGUARDANDO,
                StatusAnaliseCompliance.EM_ANALISE,
                StatusAnaliseCompliance.APROVADO,
                StatusAnaliseCompliance.ATRIBUIDO
            ]
        ).first()
        
        if not analise_existente:
            # Cria nova análise de compliance
            AnaliseCompliance.objects.create(
                lead=instance.lead,
                valor_divida_total=None,  
                status=StatusAnaliseCompliance.AGUARDANDO
            )
            
            # Atualiza status do lead para EM_COMPLIANCE
            instance.lead.status = 'EM_COMPLIANCE'
            instance.lead.passou_compliance = False
            instance.lead.save(update_fields=['status', 'passou_compliance'])
