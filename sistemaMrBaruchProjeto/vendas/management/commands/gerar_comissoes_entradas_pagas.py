"""
Comando para gerar comissões retroativas de entradas pagas.

Busca vendas com:
- status_pagamento_entrada='PAGO'
- valor_entrada > 0
- Sem comissões do tipo CONSULTOR_ENTRADA ou CAPTADOR_ENTRADA

E cria as comissões usando o CommissionService.
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from vendas.models import Venda
from financeiro.models import Comissao
from core.commission_service import CommissionService


class Command(BaseCommand):
    help = 'Gera comissões retroativas para entradas pagas que não possuem comissões'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Apenas mostra o que seria feito, sem criar comissões',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.WARNING('=' * 80))
        self.stdout.write(self.style.WARNING('GERADOR DE COMISSÕES RETROATIVAS - ENTRADAS PAGAS'))
        self.stdout.write(self.style.WARNING('=' * 80))
        
        if dry_run:
            self.stdout.write(self.style.NOTICE('\n⚠️  MODO DRY-RUN: Nenhuma comissão será criada\n'))
        
        # Buscar vendas com entrada paga
        vendas_entrada_paga = Venda.objects.filter(
            status_pagamento_entrada='PAGO',
            valor_entrada__gt=0
        ).select_related('captador', 'consultor', 'cliente')
        
        self.stdout.write(f'📊 Total de vendas com entrada PAGA: {vendas_entrada_paga.count()}\n')
        
        # Para cada venda, verificar se já tem comissões de entrada
        vendas_sem_comissao = []
        
        for venda in vendas_entrada_paga:
            # Verificar se já existe comissão de entrada (captador ou consultor)
            tem_comissao = Comissao.objects.filter(
                venda=venda,
                tipo_comissao__in=['CAPTADOR_ENTRADA', 'CONSULTOR_ENTRADA']
            ).exists()
            
            if not tem_comissao:
                vendas_sem_comissao.append(venda)
        
        self.stdout.write(f'🔍 Vendas SEM comissões de entrada: {len(vendas_sem_comissao)}\n')
        
        if not vendas_sem_comissao:
            self.stdout.write(self.style.SUCCESS('✅ Todas as entradas pagas já possuem comissões!\n'))
            return
        
        # Criar comissões
        total_criadas = 0
        total_erros = 0
        
        for venda in vendas_sem_comissao:
            self.stdout.write(f'\n📦 Processando Venda #{venda.id}:')
            self.stdout.write(f'   Cliente: {venda.cliente.lead.nome_completo if hasattr(venda.cliente, "lead") else "N/A"}')
            self.stdout.write(f'   Entrada: R$ {venda.valor_entrada:.2f}')
            self.stdout.write(f'   Captador: {venda.captador.get_full_name() or venda.captador.email}')
            self.stdout.write(f'   Consultor: {venda.consultor.get_full_name() or venda.consultor.email}')
            
            if dry_run:
                self.stdout.write(self.style.NOTICE('   ⚠️  [DRY-RUN] Comissões NÃO foram criadas'))
                continue
            
            try:
                # Criar comissões usando o serviço
                comissoes = CommissionService.criar_comissao_entrada_venda(venda)
                
                if comissoes.get('captador'):
                    self.stdout.write(self.style.SUCCESS(
                        f'   ✅ Comissão CAPTADOR criada: R$ {comissoes["captador"].valor_comissao:.2f} '
                        f'({comissoes["captador"].percentual_comissao}%)'
                    ))
                    total_criadas += 1
                
                if comissoes.get('consultor'):
                    self.stdout.write(self.style.SUCCESS(
                        f'   ✅ Comissão CONSULTOR criada: R$ {comissoes["consultor"].valor_comissao:.2f} '
                        f'({comissoes["consultor"].percentual_comissao}%)'
                    ))
                    total_criadas += 1
                else:
                    self.stdout.write(self.style.WARNING(
                        f'   ⚠️  Comissão CONSULTOR não criada (faturamento insuficiente)'
                    ))
                
            except Exception as e:
                total_erros += 1
                self.stdout.write(self.style.ERROR(f'   ❌ ERRO: {str(e)}'))
        
        # Resumo final
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS(f'✅ Total de comissões criadas: {total_criadas}'))
        if total_erros > 0:
            self.stdout.write(self.style.ERROR(f'❌ Total de erros: {total_erros}'))
        self.stdout.write('=' * 80 + '\n')
