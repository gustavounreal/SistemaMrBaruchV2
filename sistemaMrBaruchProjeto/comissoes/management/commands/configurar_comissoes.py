from django.core.management.base import BaseCommand
from core.models import ConfiguracaoSistema

class Command(BaseCommand):
    help = 'Configura os parâmetros de comissões no sistema'

    def handle(self, *args, **options):
        """Cria ou atualiza configurações de comissão"""
        
        configuracoes = [
            {
                'chave': 'COMISSAO_ATIVA',
                'valor': 'true',
                'descricao': 'Ativar/desativar sistema de comissões automático',
                'tipo': 'BOOLEANO'
            },
            {
                'chave': 'COMISSAO_ATENDENTE_VALOR_FIXO',
                'valor': '0.50',
                'descricao': 'Valor fixo de comissão por levantamento de lead com pagamento PIX confirmado',
                'tipo': 'NUMERO'
            },
            {
                'chave': 'COMISSAO_CAPTADOR_PERCENTUAL',
                'valor': '3',
                'descricao': 'Percentual de comissão para captadores externos (%)',
                'tipo': 'NUMERO'
            },
            {
                'chave': 'COMISSAO_VENDAS_MIN',
                'valor': '2',
                'descricao': 'Percentual mínimo de comissão sobre vendas (%)',
                'tipo': 'NUMERO'
            },
            {
                'chave': 'COMISSAO_VENDAS_MAX',
                'valor': '10',
                'descricao': 'Percentual máximo de comissão sobre vendas (%)',
                'tipo': 'NUMERO'
            },
        ]
        
        criados = 0
        atualizados = 0
        
        for config_data in configuracoes:
            config, created = ConfiguracaoSistema.objects.update_or_create(
                chave=config_data['chave'],
                defaults={
                    'valor': config_data['valor'],
                    'descricao': config_data['descricao'],
                    'tipo': config_data['tipo'],
                }
            )
            
            if created:
                criados += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Criada: {config.chave} = {config.valor}'))
            else:
                atualizados += 1
                self.stdout.write(self.style.WARNING(f'↻ Atualizada: {config.chave} = {config.valor}'))
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Configurações processadas: {criados} criadas, {atualizados} atualizadas'))
        self.stdout.write(self.style.SUCCESS('Acesse /core/painel_configuracoes/ para ajustar os valores'))
