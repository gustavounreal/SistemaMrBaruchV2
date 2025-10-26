# compliance/management/commands/criar_analises_leads_pagos.py
from django.core.management.base import BaseCommand
from django.db import transaction
from marketing.models import Lead
from financeiro.models import PixLevantamento
from compliance.models import AnaliseCompliance, StatusAnaliseCompliance


class Command(BaseCommand):
    help = 'Cria análises de Compliance para leads com levantamento pago mas sem análise'

    def handle(self, *args, **options):
        self.stdout.write('Buscando leads com levantamento pago...')
        
        # Buscar todos os leads com PIX pago
        leads_com_pix_pago = Lead.objects.filter(
            pix_levantamentos__status_pagamento='pago'
        ).distinct()
        
        total_processados = 0
        total_criados = 0
        total_ja_existiam = 0
        
        for lead in leads_com_pix_pago:
            total_processados += 1
            
            # Verificar se já existe análise
            analise_existente = AnaliseCompliance.objects.filter(lead=lead).first()
            
            if analise_existente:
                total_ja_existiam += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'  ⚠ Lead #{lead.id} ({lead.nome_completo}) - Já tem análise #{analise_existente.id}'
                    )
                )
            else:
                # Buscar o PIX mais recente
                pix = lead.pix_levantamentos.filter(status_pagamento='pago').order_by('-data_criacao').first()
                
                with transaction.atomic():
                    # Criar análise
                    analise = AnaliseCompliance.objects.create(
                        lead=lead,
                        valor_divida_total=None,
                        status=StatusAnaliseCompliance.AGUARDANDO
                    )
                    
                    # Atualizar status do lead
                    lead.status = 'EM_COMPLIANCE'
                    lead.passou_compliance = False
                    lead.save(update_fields=['status', 'passou_compliance'])
                    
                    total_criados += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✓ Lead #{lead.id} ({lead.nome_completo}) - Análise #{analise.id} criada'
                        )
                    )
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS(f'Total de leads processados: {total_processados}'))
        self.stdout.write(self.style.SUCCESS(f'Análises criadas: {total_criados}'))
        self.stdout.write(self.style.WARNING(f'Análises já existentes: {total_ja_existiam}'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        
        if total_criados > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ {total_criados} lead(s) agora estão disponíveis no painel de Compliance!'
                )
            )
