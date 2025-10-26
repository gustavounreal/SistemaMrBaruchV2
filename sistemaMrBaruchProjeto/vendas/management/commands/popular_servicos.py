"""
Comando para popular o banco de dados com os serviços pré-definidos
Uso: python manage.py popular_servicos
"""
from django.core.management.base import BaseCommand
from vendas.models import Servico
from decimal import Decimal


class Command(BaseCommand):
    help = 'Popula o banco de dados com os serviços pré-definidos'

    def handle(self, *args, **options):
        servicos_data = [
            {
                'nome': 'Limpa Nome',
                'tipo': 'LIMPA_NOME',
                'descricao': 'Serviço de limpeza de nome - remoção de restrições cadastrais',
                'prazo_medio': 60,
                'preco_base': Decimal('800.00'),
            },
            {
                'nome': 'Retirada de Travas',
                'tipo': 'RETIRADA_TRAVAS',
                'descricao': 'Serviço de retirada de travas bancárias e financeiras',
                'prazo_medio': 45,
                'preco_base': Decimal('600.00'),
            },
            {
                'nome': 'Recuperação de Score',
                'tipo': 'RECUPERACAO_SCORE',
                'descricao': 'Serviço de recuperação e melhoria de score de crédito',
                'prazo_medio': 90,
                'preco_base': Decimal('1200.00'),
            },
            {
                'nome': 'Limpa Nome + Recuperação de Score',
                'tipo': 'COMBINADO',
                'descricao': 'Pacote combinado: Limpeza de Nome + Recuperação de Score',
                'prazo_medio': 90,
                'preco_base': Decimal('1800.00'),
            },
            {
                'nome': 'Limpa Nome + Retirada de Travas',
                'tipo': 'COMBINADO',
                'descricao': 'Pacote combinado: Limpeza de Nome + Retirada de Travas',
                'prazo_medio': 75,
                'preco_base': Decimal('1300.00'),
            },
            {
                'nome': 'Recuperação de Score + Retirada de Travas',
                'tipo': 'COMBINADO',
                'descricao': 'Pacote combinado: Recuperação de Score + Retirada de Travas',
                'prazo_medio': 90,
                'preco_base': Decimal('1600.00'),
            },
            {
                'nome': 'Limpa Nome + Recuperação de Score + Retirada de Travas',
                'tipo': 'COMBINADO',
                'descricao': 'Pacote completo: Limpeza de Nome + Recuperação de Score + Retirada de Travas',
                'prazo_medio': 120,
                'preco_base': Decimal('2500.00'),
            },
        ]

        criados = 0
        atualizados = 0
        
        for servico_data in servicos_data:
            servico, created = Servico.objects.update_or_create(
                nome=servico_data['nome'],
                defaults={
                    'tipo': servico_data['tipo'],
                    'descricao': servico_data['descricao'],
                    'prazo_medio': servico_data['prazo_medio'],
                    'preco_base': servico_data['preco_base'],
                    'ativo': True,
                }
            )
            
            if created:
                criados += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Criado: {servico.nome}')
                )
            else:
                atualizados += 1
                self.stdout.write(
                    self.style.WARNING(f'↻ Atualizado: {servico.nome}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n{"="*60}\n'
                f'Resumo:\n'
                f'  • Serviços criados: {criados}\n'
                f'  • Serviços atualizados: {atualizados}\n'
                f'  • Total: {criados + atualizados}\n'
                f'{"="*60}'
            )
        )
