"""
Comando para migrar usuários do grupo 'cliente' para 'captador'
exceto aqueles que foram criados automaticamente via vendas
(que têm referência em Cliente.usuario_portal)

Uso: python manage.py migrar_clientes_para_captadores
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Migra usuários do grupo cliente para captador (exceto clientes de vendas)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Apenas simula a migração sem aplicar mudanças',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('MIGRAÇÃO DE GRUPOS: cliente → captador'))
        self.stdout.write(self.style.WARNING('=' * 70))
        
        if dry_run:
            self.stdout.write(self.style.NOTICE('\n⚠️  MODO DRY-RUN (simulação) - Nenhuma alteração será feita\n'))
        
        # Obter grupos
        try:
            grupo_cliente = Group.objects.get(name='cliente')
        except Group.DoesNotExist:
            self.stdout.write(self.style.ERROR('❌ Grupo "cliente" não encontrado!'))
            return
        
        grupo_captador, created = Group.objects.get_or_create(name='captador')
        if created:
            self.stdout.write(self.style.SUCCESS('✅ Grupo "captador" criado'))
        
        # Buscar usuários no grupo 'cliente'
        usuarios_clientes = User.objects.filter(groups=grupo_cliente)
        total_usuarios = usuarios_clientes.count()
        
        self.stdout.write(f'\n📊 Total de usuários no grupo "cliente": {total_usuarios}\n')
        
        if total_usuarios == 0:
            self.stdout.write(self.style.SUCCESS('✅ Nenhum usuário para migrar.'))
            return
        
        # Separar usuários
        usuarios_para_migrar = []
        usuarios_clientes_reais = []
        
        from clientes.models import Cliente
        
        for user in usuarios_clientes:
            # Verificar se é um cliente real (tem referência em Cliente.usuario_portal)
            is_cliente_real = Cliente.objects.filter(usuario_portal=user).exists()
            
            if is_cliente_real:
                usuarios_clientes_reais.append(user)
            else:
                usuarios_para_migrar.append(user)
        
        self.stdout.write(f'👥 Clientes reais (permanecem no grupo "cliente"): {len(usuarios_clientes_reais)}')
        self.stdout.write(f'🔄 Usuários a migrar para "captador": {len(usuarios_para_migrar)}\n')
        
        # Listar usuários a migrar
        if usuarios_para_migrar:
            self.stdout.write(self.style.WARNING('Usuários que serão migrados:'))
            for user in usuarios_para_migrar:
                nome_completo = f"{user.first_name} {user.last_name}".strip() or user.username
                self.stdout.write(f'  • {nome_completo} (@{user.username}) - {user.email}')
        
        # Listar clientes reais que permanecerão
        if usuarios_clientes_reais:
            self.stdout.write(self.style.SUCCESS('\nClientes reais que permanecerão no grupo "cliente":'))
            for user in usuarios_clientes_reais:
                nome_completo = f"{user.first_name} {user.last_name}".strip() or user.username
                self.stdout.write(f'  • {nome_completo} (@{user.username}) - {user.email}')
        
        # Confirmar migração
        if not dry_run and usuarios_para_migrar:
            self.stdout.write(self.style.WARNING('\n⚠️  Confirmar migração? (digite "sim" para continuar): '), ending='')
            confirmacao = input().strip().lower()
            
            if confirmacao != 'sim':
                self.stdout.write(self.style.ERROR('❌ Migração cancelada pelo usuário.'))
                return
            
            # Executar migração
            self.stdout.write('\n🔄 Migrando usuários...\n')
            migrados = 0
            
            for user in usuarios_para_migrar:
                try:
                    user.groups.remove(grupo_cliente)
                    user.groups.add(grupo_captador)
                    migrados += 1
                    nome_completo = f"{user.first_name} {user.last_name}".strip() or user.username
                    self.stdout.write(self.style.SUCCESS(f'  ✅ {nome_completo} (@{user.username})'))
                except Exception as e:
                    nome_completo = f"{user.first_name} {user.last_name}".strip() or user.username
                    self.stdout.write(self.style.ERROR(f'  ❌ {nome_completo} (@{user.username}): {e}'))
            
            self.stdout.write(self.style.SUCCESS(f'\n✅ Migração concluída! {migrados} usuários migrados.'))
        elif dry_run:
            self.stdout.write(self.style.NOTICE('\n✅ Simulação concluída. Use sem --dry-run para aplicar.'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ Nenhum usuário precisa ser migrado.'))
