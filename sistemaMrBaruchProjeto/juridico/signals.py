from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from vendas.models import Venda
from financeiro.models import Parcela
from .models import Contrato


@receiver(post_save, sender=Parcela)
def criar_contrato_ao_confirmar_entrada(sender, instance, created, **kwargs):
    """
    Cria automaticamente um contrato com status 'AGUARDANDO_GERACAO'
    quando a primeira parcela (entrada) for confirmada como paga.
    """
    # Verifica se é a primeira parcela (entrada) e se está paga
    if instance.numero_parcela == 0 and instance.status == 'PAGO':
        venda = instance.venda
        
        # Verifica se já existe contrato para esta venda
        contrato_existe = Contrato.objects.filter(venda=venda).exists()
        
        if not contrato_existe:
            # Cria o contrato com status aguardando geração
            Contrato.objects.create(
                venda=venda,
                cliente=venda.cliente,
                status='AGUARDANDO_GERACAO',
            )
            print(f"✅ Contrato criado automaticamente para venda #{venda.id}")


@receiver(post_save, sender=Venda)
def criar_contrato_para_venda_sem_entrada(sender, instance, created, **kwargs):
    """
    Cria contrato para vendas que não possuem valor de entrada
    """
    if created and instance.sem_entrada:
        # Verifica se já existe contrato
        contrato_existe = Contrato.objects.filter(venda=instance).exists()
        
        if not contrato_existe:
            Contrato.objects.create(
                venda=instance,
                cliente=instance.cliente,
                status='AGUARDANDO_GERACAO',
            )
            print(f"✅ Contrato criado automaticamente para venda sem entrada #{instance.id}")
