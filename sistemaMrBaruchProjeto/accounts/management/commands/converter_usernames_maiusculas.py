from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Converte todos os usernames existentes para MAIÚSCULAS'

    def handle(self, *args, **options):
        usuarios = User.objects.all()
        total = usuarios.count()
        convertidos = 0
        
        self.stdout.write(self.style.WARNING(f'Encontrados {total} usuários no sistema.'))
        self.stdout.write(self.style.WARNING('Convertendo usernames para MAIÚSCULAS...\n'))
        
        for usuario in usuarios:
            username_original = usuario.username
            username_maiusculo = username_original.upper()
            
            if username_original != username_maiusculo:
                usuario.username = username_maiusculo
                usuario.save()
                convertidos += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ {username_original} → {username_maiusculo}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'○ {username_original} (já estava em maiúsculas)')
                )
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(f'\n✅ Processo concluído!'))
        self.stdout.write(self.style.SUCCESS(f'   Total de usuários: {total}'))
        self.stdout.write(self.style.SUCCESS(f'   Convertidos: {convertidos}'))
        self.stdout.write(self.style.SUCCESS(f'   Já estavam corretos: {total - convertidos}\n'))
