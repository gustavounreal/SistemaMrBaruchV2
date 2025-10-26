from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission


class Command(BaseCommand):
    help = 'Cria grupos padrão do sistema e configura permissões iniciais'

    def handle(self, *args, **options):
       
        grupos = [
            'atendente',
            'captador',
            'financeiro',
            'gestor',
            'admin',
            'funcionarios',
            'clientes',
        ]

        for nome in grupos:
            group, created = Group.objects.get_or_create(name=nome)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Grupo "{nome}" criado.'))
            else:
                self.stdout.write(f'Grupo "{nome}" já existe.')

        # Atribuir todas as permissões ao grupo 'admin' para garantir acesso amplo
        try:
            admin_group = Group.objects.get(name='admin')
            all_perms = Permission.objects.all()
            admin_group.permissions.set(all_perms)
            self.stdout.write(self.style.SUCCESS('Todas as permissões atribuídas ao grupo "admin".'))
        except Group.DoesNotExist:
            self.stdout.write(self.style.ERROR('Grupo "admin" não encontrado para atribuir permissões.'))
