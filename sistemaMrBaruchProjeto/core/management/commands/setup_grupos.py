# core/management/commands/setup_grupos.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group


class Command(BaseCommand):
    help = 'Cria e configura os grupos de usuários do sistema'

    def handle(self, *args, **options):
        self.stdout.write('Configurando grupos de usuários...')
        
        # Grupos que devem existir no sistema
        grupos_sistema = [
            ('admin', 'Administradores do sistema'),
            ('atendente', 'Atendentes de leads'),
            ('captador', 'Captadores de leads'),
            ('compliance', 'Equipe de compliance'),
            ('comercial1', 'Consultores comerciais 1'),
            ('comercial2', 'Consultores comerciais 2'),
            ('cliente', 'Clientes do sistema'),
            ('financeiro', 'Equipe financeira'),
            ('administrativo', 'Equipe administrativa'),
            ('retencao', 'Equipe de retenção'),
            ('relacionamento', 'Equipe de relacionamento'),
        ]
        
        # Renomear grupo "consultor" para "comercial1" se existir
        try:
            consultor_group = Group.objects.get(name='consultor')
            consultor_group.name = 'comercial1'
            consultor_group.save()
            self.stdout.write(
                self.style.SUCCESS('✓ Grupo "consultor" renomeado para "comercial1"')
            )
        except Group.DoesNotExist:
            pass
        
        # Remover grupo "gestor" se existir (substituído por admin)
        try:
            gestor_group = Group.objects.get(name='gestor')
            # Mover usuários do gestor para admin
            admin_group, _ = Group.objects.get_or_create(name='admin')
            for user in gestor_group.user_set.all():
                admin_group.user_set.add(user)
            gestor_group.delete()
            self.stdout.write(
                self.style.SUCCESS('✓ Grupo "gestor" removido (usuários movidos para "admin")')
            )
        except Group.DoesNotExist:
            pass
        
        # Renomear "clientes" para "cliente"
        try:
            clientes_group = Group.objects.get(name='clientes')
            clientes_group.name = 'cliente'
            clientes_group.save()
            self.stdout.write(
                self.style.SUCCESS('✓ Grupo "clientes" renomeado para "cliente"')
            )
        except Group.DoesNotExist:
            pass
        
        # Criar grupos que não existem
        total_criados = 0
        for nome_grupo, descricao in grupos_sistema:
            grupo, created = Group.objects.get_or_create(name=nome_grupo)
            if created:
                total_criados += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Grupo "{nome_grupo}" criado - {descricao}')
                )
        
        # Listar todos os grupos finais
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS(f'Total de grupos criados: {total_criados}'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        self.stdout.write('Grupos configurados no sistema:')
        for grupo in Group.objects.all().order_by('name'):
            usuarios_count = grupo.user_set.count()
            self.stdout.write(f'  • {grupo.name} ({usuarios_count} usuários)')
        
        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS('✓ Configuração de grupos concluída!')
        )
