from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Cria o grupo Admin com acesso total e adiciona todos os superusuários a esse grupo'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        
        # Criar grupo Admin
        admin_group, created = Group.objects.get_or_create(name='admin')
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Grupo "admin" criado com sucesso'))
        else:
            self.stdout.write(self.style.WARNING('→ Grupo "admin" já existe'))
        
        # Adicionar TODAS as permissões ao grupo Admin
        all_permissions = Permission.objects.all()
        admin_group.permissions.set(all_permissions)
        self.stdout.write(self.style.SUCCESS(f'✓ {all_permissions.count()} permissões adicionadas ao grupo admin'))
        
        # Adicionar todos os superusuários ao grupo admin
        superusers = User.objects.filter(is_superuser=True)
        count = 0
        for user in superusers:
            if not user.groups.filter(name='admin').exists():
                user.groups.add(admin_group)
                count += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Superusuário "{user.username}" adicionado ao grupo admin'))
            else:
                self.stdout.write(self.style.WARNING(f'→ Superusuário "{user.username}" já está no grupo admin'))
        
        if count == 0 and superusers.count() > 0:
            self.stdout.write(self.style.WARNING('→ Todos os superusuários já estavam no grupo admin'))
        elif superusers.count() == 0:
            self.stdout.write(self.style.WARNING('⚠ Nenhum superusuário encontrado no sistema'))
            self.stdout.write(self.style.WARNING('  Crie um superusuário com: python manage.py createsuperuser'))
        
        self.stdout.write(self.style.SUCCESS('\n✓ Configuração concluída!'))
        self.stdout.write(self.style.SUCCESS(f'  - Grupo admin: {admin_group.permissions.count()} permissões'))
        self.stdout.write(self.style.SUCCESS(f'  - Superusuários no grupo: {admin_group.user_set.filter(is_superuser=True).count()}'))
