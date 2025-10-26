from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Núcleo do Sistema'
    
    def ready(self):
        """Importa signals quando app estiver pronto"""
        import core.signals_comissoes  # noqa