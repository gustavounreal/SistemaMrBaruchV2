"""
Comando para sincronizar dados do Asaas Alternativo em background
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from asaas_sync.services import AsaasSyncService
from accounts.models import CustomUser
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sincroniza dados da conta Asaas alternativa'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limite-clientes',
            type=int,
            default=None,
            help='Limite de clientes a sincronizar'
        )

    def handle(self, *args, **options):
        limite_clientes = options.get('limite_clientes')
        
        try:
            # Buscar token alternativo
            token_alternativo = getattr(settings, 'ASAAS_ALTERNATIVO_TOKEN', None)
            
            if not token_alternativo:
                self.stdout.write(self.style.ERROR('❌ ASAAS_ALTERNATIVO_TOKEN não configurado'))
                return
            
            self.stdout.write(self.style.SUCCESS(f'🔑 Token alternativo encontrado'))
            
            # Criar serviço de sincronização
            sync_service = AsaasSyncService()
            
            # Forçar produção
            url_producao = 'https://api.asaas.com/v3'
            
            # Substituir token temporariamente
            token_original = sync_service.api_token
            url_original = sync_service.base_url
            
            sync_service.api_token = token_alternativo
            sync_service.base_url = url_producao
            sync_service.headers['access_token'] = token_alternativo
            
            self.stdout.write(self.style.SUCCESS(f'🌐 URL: {url_producao}'))
            
            try:
                # Buscar usuário admin para o log
                usuario = CustomUser.objects.filter(is_superuser=True).first()
                
                self.stdout.write(self.style.SUCCESS('🔄 Iniciando sincronização...'))
                
                # Executar sincronização
                log = sync_service.sincronizar_tudo(
                    usuario=usuario,
                    limite_clientes=limite_clientes
                )
                
                self.stdout.write(self.style.SUCCESS('✅ Sincronização concluída!'))
                self.stdout.write(f'Status: {log.status}')
                self.stdout.write(f'Clientes: {log.total_clientes} ({log.clientes_novos} novos)')
                self.stdout.write(f'Cobranças: {log.total_cobrancas} ({log.cobrancas_novas} novas)')
                self.stdout.write(f'Duração: {log.duracao_segundos}s')
                
                if log.mensagem:
                    self.stdout.write(f'Mensagem: {log.mensagem}')
                    
            finally:
                # Restaurar token original
                sync_service.api_token = token_original
                sync_service.base_url = url_original
                sync_service.headers['access_token'] = token_original
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Erro: {str(e)}'))
            logger.error(f'Erro na sincronização alternativa: {str(e)}', exc_info=True)
            raise
