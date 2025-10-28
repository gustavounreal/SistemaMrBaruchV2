# vendas/management/commands/corrigir_leads_comercial2_compliance.py
"""
Comando para corrigir leads convertidos no Comercial 2 que não apareceram no Compliance.
Cria as análises de compliance faltantes.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from vendas.models import RepescagemLead
from compliance.models import AnaliseCompliance, StatusAnaliseCompliance
from compliance.models import HistoricoAnaliseCompliance


class Command(BaseCommand):
    help = 'Corrige leads convertidos no Comercial 2 que não têm análise de Compliance'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando correção de leads do Comercial 2...'))
        
        # Buscar repescagens convertidas
        repescagens_convertidas = RepescagemLead.objects.filter(
            status='CONVERTIDO'
        ).select_related('lead')
        
        total = repescagens_convertidas.count()
        corrigidos = 0
        ja_existentes = 0
        
        for repescagem in repescagens_convertidas:
            lead = repescagem.lead
            
            # Verificar se já existe análise de compliance
            analise_existente = AnaliseCompliance.objects.filter(
                lead=lead
            ).first()
            
            if not analise_existente:
                # Criar análise de compliance
                analise = AnaliseCompliance.objects.create(
                    lead=lead,
                    status=StatusAnaliseCompliance.AGUARDANDO,
                    observacoes_analise=f'Lead convertido pelo Comercial 2 (Repescagem #{repescagem.id}) - Criado via comando de correção'
                )
                try:
                    HistoricoAnaliseCompliance.objects.create(
                        analise=analise,
                        acao='CRIA_COMERCIAL2',
                        usuario=None,
                        descricao=(
                            f'Análise criada automaticamente após conversão no Comercial 2 (Repescagem #{repescagem.id})'
                        )
                    )
                except Exception:
                    pass
                
                # Atualizar status do lead
                lead.status = 'EM_COMPLIANCE'
                lead.passou_compliance = False
                lead.save()
                
                # Remover pré-vendas antigas
                preventas_antigas = lead.pre_vendas.all()
                if preventas_antigas.exists():
                    count_preventas = preventas_antigas.count()
                    preventas_antigas.delete()
                    self.stdout.write(
                        self.style.WARNING(
                            f'  └─ Removidas {count_preventas} pré-venda(s) antiga(s)'
                        )
                    )
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Criada análise para: {lead.nome_completo} (ID: {lead.id})'
                    )
                )
                corrigidos += 1
            else:
                # IMPORTANTE: Se o lead veio do Comercial 2, SEMPRE resetar para AGUARDANDO
                # independente do status atual (pode estar ATRIBUÍDO, APROVADO, etc)
                if analise_existente.status in [
                    StatusAnaliseCompliance.REPROVADO,
                    StatusAnaliseCompliance.APROVADO,
                    StatusAnaliseCompliance.ATRIBUIDO,
                    StatusAnaliseCompliance.EM_ANALISE
                ]:
                    status_anterior = analise_existente.get_status_display()
                    
                    # Resetar para aguardando análise
                    analise_existente.status = StatusAnaliseCompliance.AGUARDANDO
                    analise_existente.consultor_atribuido = None
                    analise_existente.data_atribuicao = None
                    analise_existente.observacoes_analise += (
                        f'\n\n[{timezone.now().strftime("%d/%m/%Y %H:%M")}] '
                        f'Lead retornou do Comercial 2 (Repescagem #{repescagem.id}) '
                        f'- Status anterior: {status_anterior} → Resetado para AGUARDANDO'
                    )
                    analise_existente.save()
                    try:
                        HistoricoAnaliseCompliance.objects.create(
                            analise=analise_existente,
                            acao='REENVIO_COMERCIAL2',
                            usuario=None,
                            descricao=(
                                f'Análise resetada para AGUARDANDO após conversão no Comercial 2 (Repescagem #{repescagem.id}). '
                                f'Status anterior: {status_anterior}'
                            )
                        )
                    except Exception:
                        pass
                    
                    # Atualizar status do lead
                    lead.status = 'EM_COMPLIANCE'
                    lead.passou_compliance = False
                    lead.save()
                    
                    # Remover pré-vendas antigas
                    preventas_antigas = lead.pre_vendas.all()
                    if preventas_antigas.exists():
                        count_preventas = preventas_antigas.count()
                        preventas_antigas.delete()
                        self.stdout.write(
                            self.style.WARNING(
                                f'  └─ Removidas {count_preventas} pré-venda(s) antiga(s)'
                            )
                        )
                    
                    self.stdout.write(
                        self.style.WARNING(
                            f'⟳ Resetada análise para: {lead.nome_completo} (Status: {status_anterior} → AGUARDANDO)'
                        )
                    )
                    corrigidos += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'- Já aguardando análise: {lead.nome_completo} (Status: {analise_existente.get_status_display()})'
                        )
                    )
                    ja_existentes += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Correção concluída!'
                f'\n  - Total de repescagens convertidas: {total}'
                f'\n  - Análises criadas/reativadas: {corrigidos}'
                f'\n  - Já existentes: {ja_existentes}'
            )
        )
