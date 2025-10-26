from django.core.management.base import BaseCommand
from core.services import ConfiguracaoService

class Command(BaseCommand):
    help = 'Configurações iniciais do sistema'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.HTTP_INFO('Inicializando configurações do sistema...'))
        
        # Chama o método centralizado do ConfiguracaoService
        resultado = ConfiguracaoService.inicializar_configs()
        
        self.stdout.write(self.style.SUCCESS(f' {resultado}'))
        self.stdout.write(self.style.SUCCESS('Configurações inicializadas com sucesso!'))