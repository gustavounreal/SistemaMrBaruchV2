from django.contrib import admin
from .models import AsaasClienteSyncronizado, AsaasCobrancaSyncronizada, AsaasSyncronizacaoLog


@admin.register(AsaasClienteSyncronizado)
class AsaasClienteSyncronizadoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'cpf_cnpj', 'email', 'telefone', 'cidade', 'estado', 'sincronizado_em']
    list_filter = ['estado', 'sincronizado_em']
    search_fields = ['nome', 'cpf_cnpj', 'email', 'asaas_customer_id']
    readonly_fields = ['asaas_customer_id', 'sincronizado_em', 'criado_em']
    
    fieldsets = (
        ('Dados do Asaas', {
            'fields': ('asaas_customer_id', 'external_reference')
        }),
        ('Dados Pessoais', {
            'fields': ('nome', 'cpf_cnpj', 'email', 'telefone', 'celular')
        }),
        ('Endereço', {
            'fields': ('cep', 'endereco', 'numero', 'complemento', 'bairro', 'cidade', 'estado')
        }),
        ('Informações Adicionais', {
            'fields': ('inscricao_municipal', 'inscricao_estadual', 'observacoes', 'notificacoes_desabilitadas')
        }),
        ('Metadados', {
            'fields': ('data_criacao_asaas', 'sincronizado_em', 'criado_em'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AsaasCobrancaSyncronizada)
class AsaasCobrancaSyncronizadaAdmin(admin.ModelAdmin):
    list_display = ['asaas_payment_id', 'cliente', 'tipo_cobranca', 'status', 'valor', 'data_vencimento', 'data_pagamento']
    list_filter = ['status', 'tipo_cobranca', 'data_vencimento']
    search_fields = ['asaas_payment_id', 'cliente__nome', 'cliente__cpf_cnpj', 'descricao']
    readonly_fields = ['asaas_payment_id', 'sincronizado_em', 'criado_em', 'esta_vencida', 'dias_vencimento']
    date_hierarchy = 'data_vencimento'
    
    fieldsets = (
        ('Dados do Asaas', {
            'fields': ('asaas_payment_id', 'cliente', 'external_reference')
        }),
        ('Dados da Cobrança', {
            'fields': ('tipo_cobranca', 'status', 'valor', 'valor_liquido', 'descricao')
        }),
        ('Datas', {
            'fields': ('data_vencimento', 'data_pagamento', 'data_criacao_asaas', 'esta_vencida', 'dias_vencimento')
        }),
        ('Links de Pagamento', {
            'fields': ('invoice_url', 'bank_slip_url', 'pix_qrcode_url', 'pix_copy_paste'),
            'classes': ('collapse',)
        }),
        ('Parcelamento', {
            'fields': ('numero_parcela', 'total_parcelas'),
            'classes': ('collapse',)
        }),
        ('Metadados', {
            'fields': ('sincronizado_em', 'criado_em'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AsaasSyncronizacaoLog)
class AsaasSyncronizacaoLogAdmin(admin.ModelAdmin):
    list_display = ['data_inicio', 'status', 'total_clientes', 'total_cobrancas', 'duracao_segundos', 'usuario']
    list_filter = ['status', 'data_inicio']
    readonly_fields = ['data_inicio', 'data_fim', 'duracao_segundos', 'total_clientes', 'clientes_novos', 
                      'clientes_atualizados', 'total_cobrancas', 'cobrancas_novas', 'cobrancas_atualizadas']
    
    fieldsets = (
        ('Informações da Sincronização', {
            'fields': ('status', 'data_inicio', 'data_fim', 'duracao_segundos', 'usuario')
        }),
        ('Estatísticas - Clientes', {
            'fields': ('total_clientes', 'clientes_novos', 'clientes_atualizados')
        }),
        ('Estatísticas - Cobranças', {
            'fields': ('total_cobrancas', 'cobrancas_novas', 'cobrancas_atualizadas')
        }),
        ('Mensagens e Erros', {
            'fields': ('mensagem', 'erros')
        }),
    )
    
    def has_add_permission(self, request):
        return False
