"""
Comando para corrigir PreVendas de leads que foram reatribuídos pelo Compliance
após terem sido recusados.

Quando um lead é reatribuído pelo Compliance, a PreVenda antiga (com status RECUSADO)
deve ser removida ou resetada para permitir nova pré-venda.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from vendas.models import PreVenda
from compliance.models import AnaliseCompliance, StatusAnaliseCompliance


class Command(BaseCommand):
    help = 'Corrige PreVendas RECUSADAS de leads reatribuídos pelo Compliance'

    def handle(self, *args, **options):
        self.stdout.write("Iniciando correção de PreVendas recusadas...")
        
        # Buscar leads que:
        # 1. Têm PreVenda com status RECUSADO
        # 2. Foram reatribuídos pelo Compliance (status ATRIBUIDO)
        # 3. Lead está com status QUALIFICADO (corrigido)
        
        preventas_recusadas = PreVenda.objects.filter(
            status='RECUSADO',
            lead__status='QUALIFICADO'  # Leads que foram corrigidos
        ).select_related('lead')
        
        total = preventas_recusadas.count()
        corrigidas = 0
        
        self.stdout.write(f"Encontradas {total} PreVendas recusadas com leads reatribuídos")
        
        with transaction.atomic():
            for prevenda in preventas_recusadas:
                lead = prevenda.lead
                
                # Verificar se o lead tem análise de compliance ATRIBUIDA
                try:
                    analise = AnaliseCompliance.objects.get(
                        lead=lead,
                        status=StatusAnaliseCompliance.ATRIBUIDO,
                        consultor_atribuido__isnull=False
                    )
                    
                    # Deletar a PreVenda recusada para permitir nova pré-venda
                    prevenda_info = f"{lead.nome_completo} (ID: {lead.id})"
                    prevenda.delete()
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ Removida PreVenda recusada: {prevenda_info} → "
                            f"Reatribuído ao consultor {analise.consultor_atribuido.username}"
                        )
                    )
                    corrigidas += 1
                    
                except AnaliseCompliance.DoesNotExist:
                    # Lead não tem análise ATRIBUIDA, não fazer nada
                    pass
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ Correção concluída!\n"
                f"  - Total de PreVendas RECUSADAS encontradas: {total}\n"
                f"  - PreVendas removidas (leads reatribuídos): {corrigidas}"
            )
        )
