# marketing/management/commands/corrigir_status_leads_atribuidos.py
"""
Comando para corrigir status de leads que foram atribuídos a consultores
mas ficaram com status APROVADO_COMPLIANCE ao invés de QUALIFICADO.
"""
from django.core.management.base import BaseCommand
from marketing.models import Lead
from compliance.models import AnaliseCompliance, StatusAnaliseCompliance


class Command(BaseCommand):
    help = 'Corrige status de leads atribuídos que estão como APROVADO_COMPLIANCE'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando correção de status de leads atribuídos...'))
        
        # Buscar leads com status APROVADO_COMPLIANCE
        leads_aprovados = Lead.objects.filter(status='APROVADO_COMPLIANCE')
        
        total = leads_aprovados.count()
        corrigidos = 0
        
        for lead in leads_aprovados:
            # Verificar se o lead tem análise com status ATRIBUIDO
            analise = AnaliseCompliance.objects.filter(
                lead=lead,
                status=StatusAnaliseCompliance.ATRIBUIDO
            ).first()
            
            if analise and analise.consultor_atribuido:
                # Lead foi atribuído a consultor, deve estar QUALIFICADO
                lead.status = 'QUALIFICADO'
                lead.passou_compliance = True
                lead.save(update_fields=['status', 'passou_compliance'])
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Corrigido: {lead.nome_completo} (ID: {lead.id}) '
                        f'→ Atribuído ao consultor {analise.consultor_atribuido.username}'
                    )
                )
                corrigidos += 1
            else:
                # Lead não tem consultor atribuído, deve continuar APROVADO_COMPLIANCE
                self.stdout.write(
                    self.style.WARNING(
                        f'- Mantido: {lead.nome_completo} (ID: {lead.id}) '
                        f'→ Sem consultor atribuído'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Correção concluída!'
                f'\n  - Total de leads APROVADO_COMPLIANCE: {total}'
                f'\n  - Leads corrigidos para QUALIFICADO: {corrigidos}'
            )
        )
