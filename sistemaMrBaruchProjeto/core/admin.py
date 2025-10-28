from django.contrib import admin
from .models import ConfiguracaoSistema, LogSistema, Notificacao, WebhookLog

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


@admin.register(WebhookLog)
class WebhookLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'tipo', 'evento', 'payment_id', 'payment_status', 'status_processamento', 'data_recebimento']
    list_filter = ['tipo', 'evento', 'status_processamento', 'data_recebimento']
    search_fields = ['payment_id', 'customer_id', 'evento']
    readonly_fields = ['data_recebimento', 'processado_em', 'payload_formatado']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('tipo', 'evento', 'status_processamento', 'ip_origem')
        }),
        ('Dados do Pagamento', {
            'fields': ('payment_id', 'customer_id', 'payment_status', 'valor')
        }),
        ('Payload', {
            'fields': ('payload_formatado', 'headers'),
            'classes': ('collapse',)
        }),
        ('Erro', {
            'fields': ('mensagem_erro',),
            'classes': ('collapse',)
        }),
        ('Datas', {
            'fields': ('data_recebimento', 'processado_em')
        }),
    )
    
    def payload_formatado(self, obj):
        return obj.payload_formatado
    payload_formatado.short_description = 'Payload (JSON)'

