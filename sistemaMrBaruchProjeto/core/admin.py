from django.contrib import admin
from .models import ConfiguracaoSistema, LogSistema, Notificacao

@admin.register(ConfiguracaoSistema)
class ConfiguracaoSistemaAdmin(admin.ModelAdmin):
        list_display = ('chave', 'valor', 'tipo', 'ultima_atualizacao', 'descricao')
        search_fields = ('chave', 'descricao')
        list_filter = ('tipo',)
        readonly_fields = ('ultima_atualizacao',)
        fieldsets = (
            (None, {
                'fields': ('chave', 'valor', 'tipo')
            }),
            ('Informações Adicionais', {
                'fields': ('descricao', 'ultima_atualizacao'),
            }),
        )
    
def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        

@admin.register(LogSistema)
class LogSistemaAdmin(admin.ModelAdmin):
    list_display = ['modulo', 'acao', 'nivel', 'usuario', 'data_criacao']
    list_filter = ['nivel', 'modulo', 'data_criacao']
    search_fields = ['mensagem', 'modulo', 'acao']
    readonly_fields = ['data_criacao']

@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'titulo', 'tipo', 'lida', 'data_criacao']
    list_filter = ['tipo', 'lida', 'data_criacao']
    search_fields = ['titulo', 'mensagem']

