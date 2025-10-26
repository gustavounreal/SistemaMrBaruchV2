"""
Comando para validar e recuperar comissões faltantes.

Uso:
    python manage.py validar_comissoes
    python manage.py validar_comissoes --dry-run
    python manage.py validar_comissoes --relatorio
"""
from django.core.management.base import BaseCommand
from core.commission_validator import CommissionValidator


class Command(BaseCommand):
    help = 'Valida e recupera comissões faltantes em todo o sistema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Apenas mostra o que seria feito, sem criar comissões',
        )
        parser.add_argument(
            '--relatorio',
            action='store_true',
            help='Gera relatório de comissões faltantes sem criar',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        relatorio_only = options['relatorio']
        
        self.stdout.write(self.style.WARNING('=' * 80))
        self.stdout.write(self.style.WARNING('VALIDADOR AUTOMÁTICO DE COMISSÕES'))
        self.stdout.write(self.style.WARNING('=' * 80))
        self.stdout.write('')
        
        if relatorio_only:
            self.stdout.write(self.style.NOTICE('📊 Gerando relatório de comissões faltantes...\n'))
            relatorio = CommissionValidator.gerar_relatorio_comissoes_faltantes()
            
            self.stdout.write(self.style.WARNING('1. PIX Levantamento sem comissão:'))
            if relatorio['pix_levantamento_sem_comissao']:
                for item in relatorio['pix_levantamento_sem_comissao']:
                    self.stdout.write(f"   - Lead #{item['lead_id']}: {item['lead_nome']} - R$ {item['valor']:.2f}")
            else:
                self.stdout.write(self.style.SUCCESS('   ✅ Nenhum PIX sem comissão'))
            
            self.stdout.write('\n' + self.style.WARNING('2. Entradas pagas sem comissão:'))
            if relatorio['entradas_pagas_sem_comissao']:
                for item in relatorio['entradas_pagas_sem_comissao']:
                    self.stdout.write(f"   - Venda #{item['venda_id']}: R$ {item['valor_entrada']:.2f}")
            else:
                self.stdout.write(self.style.SUCCESS('   ✅ Nenhuma entrada sem comissão'))
            
            self.stdout.write('\n' + self.style.WARNING('3. Parcelas pagas sem comissão:'))
            if relatorio['parcelas_pagas_sem_comissao']:
                for item in relatorio['parcelas_pagas_sem_comissao'][:20]:  # Primeiras 20
                    self.stdout.write(f"   - Parcela #{item['parcela_id']} (Venda #{item['venda_id']}): R$ {item['valor']:.2f}")
                if len(relatorio['parcelas_pagas_sem_comissao']) > 20:
                    self.stdout.write(f"   ... e mais {len(relatorio['parcelas_pagas_sem_comissao']) - 20}")
            else:
                self.stdout.write(self.style.SUCCESS('   ✅ Nenhuma parcela sem comissão'))
            
            self.stdout.write('\n' + '=' * 80)
            return
        
        if dry_run:
            self.stdout.write(self.style.NOTICE('⚠️  MODO DRY-RUN: Simulação apenas, nenhuma comissão será criada\n'))
        
        # Executar validação completa
        if not dry_run:
            stats = CommissionValidator.validar_e_recuperar_todas_comissoes()
            
            self.stdout.write('\n' + '=' * 80)
            self.stdout.write(self.style.SUCCESS('✅ VALIDAÇÃO CONCLUÍDA'))
            self.stdout.write('=' * 80)
            self.stdout.write(f"Comissões de atendente criadas: {stats['comissoes_atendente_criadas']}")
            self.stdout.write(f"Comissões de entrada criadas: {stats['comissoes_entrada_criadas']}")
            self.stdout.write(f"Comissões de parcelas criadas: {stats['comissoes_parcela_criadas']}")
            if stats['erros'] > 0:
                self.stdout.write(self.style.ERROR(f"Erros encontrados: {stats['erros']}"))
            self.stdout.write('=' * 80 + '\n')
        else:
            # Dry run - apenas mostrar relatório
            relatorio = CommissionValidator.gerar_relatorio_comissoes_faltantes()
            total = (
                len(relatorio['pix_levantamento_sem_comissao']) +
                len(relatorio['entradas_pagas_sem_comissao']) +
                len(relatorio['parcelas_pagas_sem_comissao'])
            )
            self.stdout.write(self.style.WARNING(f'\n📊 Total de comissões que seriam criadas: {total}\n'))
