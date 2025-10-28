"""
Signals para o módulo de vendas
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import PreVenda, RepescagemLead


@receiver(post_save, sender=PreVenda)
def criar_repescagem_automatica(sender, instance, created, **kwargs):
    """
    Cria automaticamente uma repescagem quando uma pré-venda é recusada
    Exceto se o motivo for "Sem interesse"
    """
    # Apenas processar se:
    # 1. Não é uma criação nova (é uma atualização)
    # 2. Status é RECUSADO
    # 3. Tem motivo de recusa
    # 4. Ainda não existe repescagem para esta pré-venda
    if not created and instance.status == 'RECUSADO' and instance.motivo_recusa_principal:
        # Verificar se o motivo não é "Sem interesse"
        motivo_sem_interesse = instance.motivo_recusa_principal.nome.lower() in [
            'sem interesse', 
            'não tem interesse',
            'sem interesse'
        ]
        
        if motivo_sem_interesse:
            # Se for sem interesse, marcar o lead como perdido e não criar repescagem
            instance.lead.status = 'PERDIDO'
            instance.lead.save()
            return
        
        # Verificar se já existe repescagem para esta pré-venda
        if not RepescagemLead.objects.filter(pre_venda=instance).exists():
            # Criar repescagem
            RepescagemLead.objects.create(
                lead=instance.lead,
                pre_venda=instance,
                motivo_recusa=instance.motivo_recusa_principal,
                consultor_original=instance.atendente,
                observacoes_consultor_original=instance.motivo_recusa or '',
                status='PENDENTE'
            )
            
            # Atualizar status do lead para indicar que está em repescagem
            # Você pode criar um novo status ou usar um existente
            # instance.lead.status = 'EM_REPESCAGEM'
            # instance.lead.save()
