from django.core.management.base import BaseCommand
from vendas.models import MotivoRecusa


class Command(BaseCommand):
    help = 'Popula a tabela MotivoRecusa com os motivos iniciais de não fechamento'

    def handle(self, *args, **options):
        motivos = [
            {"nome": "Valor (Achou caro)", "ordem": 1, "cor": "#dc3545"},
            {"nome": "Parcela alta", "ordem": 2, "cor": "#fd7e14"},
            {"nome": "Sem entrada", "ordem": 3, "cor": "#ffc107"},
            {"nome": "Prazo", "ordem": 4, "cor": "#17a2b8"},
            {"nome": "Desconfiança", "ordem": 5, "cor": "#6c757d"},
            {"nome": "Mau Atendimento", "ordem": 6, "cor": "#e83e8c"},
            {"nome": "Sem interesse", "ordem": 7, "cor": "#6f42c1"},
            {"nome": "Sem resposta", "ordem": 8, "cor": "#20c997"},
            {"nome": "Outros", "ordem": 9, "cor": "#6c757d"},
        ]

        for motivo_data in motivos:
            motivo, created = MotivoRecusa.objects.get_or_create(
                nome=motivo_data["nome"],
                defaults={
                    "ordem": motivo_data["ordem"],
                    "cor": motivo_data["cor"],
                    "ativo": True
                }
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Motivo criado: {motivo.nome}')
                )
            else:
                self.stdout.write(
                    f'○ Motivo já existe: {motivo.nome}'
                )

        self.stdout.write(
            self.style.SUCCESS(f'\n✓ Processo concluído! Total de motivos: {MotivoRecusa.objects.count()}')
        )
