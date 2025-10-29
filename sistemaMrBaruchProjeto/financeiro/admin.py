from django.contrib import admin
from .models import (
    Parcela, Comissao, PixLevantamento, PixEntrada, ClienteAsaas,
    Renegociacao, HistoricoContatoRetencao
)

@admin.register(PixEntrada)
class PixEntradaAdmin(admin.ModelAdmin):
    list_display = ('venda', 'valor', 'status_pagamento', 'data_criacao', 'asaas_payment_id')
    list_filter = ('status_pagamento', 'data_criacao')
    search_fields = ('venda__id', 'asaas_payment_id', 'venda__cliente__nome_completo')
    readonly_fields = ('asaas_payment_id', 'pix_code', 'pix_qr_code_url', 'data_criacao', 'data_pagamento')
    
    fieldsets = (
        ('Informações da Venda', {
            'fields': ('venda', 'valor')
        }),
        ('PIX', {
            'fields': ('asaas_payment_id', 'pix_code', 'pix_qr_code_url')
        }),
        ('Status', {
            'fields': ('status_pagamento', 'data_criacao', 'data_pagamento')
        }),
    )

@admin.register(PixLevantamento)
class PixLevantamentoAdmin(admin.ModelAdmin):
    list_display = ('lead', 'valor', 'status_pagamento', 'data_criacao', 'asaas_payment_id')
    list_filter = ('status_pagamento', 'data_criacao')
    search_fields = ('lead__nome_completo', 'asaas_payment_id')
    readonly_fields = ('asaas_payment_id', 'pix_code', 'pix_qr_code_url', 'data_criacao')

@admin.register(Parcela)
class ParcelaAdmin(admin.ModelAdmin):
    list_display = ('venda', 'numero_parcela', 'valor', 'data_vencimento', 'status')
    list_filter = ('status', 'data_vencimento')
    search_fields = ('venda__id', 'venda__cliente__nome_completo')

@admin.register(Comissao)
class ComissaoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'venda', 'tipo_comissao', 'valor_comissao', 'status', 'data_calculada')
    list_filter = ('tipo_comissao', 'status', 'data_calculada')
    search_fields = ('usuario__username', 'venda__id')

@admin.register(ClienteAsaas)
class ClienteAsaasAdmin(admin.ModelAdmin):
    list_display = ('lead', 'asaas_customer_id', 'data_criacao')
    search_fields = ('lead__nome_completo', 'asaas_customer_id')
    readonly_fields = ('asaas_customer_id', 'data_criacao')

@admin.register(Renegociacao)
class RenegociacaoAdmin(admin.ModelAdmin):
    list_display = ('id', 'venda', 'tipo_renegociacao', 'valor_novo_total', 'status', 'data_criacao', 'responsavel')
    list_filter = ('status', 'tipo_renegociacao', 'data_criacao')
    search_fields = ('venda__id', 'venda__lead__nome_completo', 'responsavel__username')
    readonly_fields = ('data_criacao', 'data_atualizacao', 'data_efetivacao')
    filter_horizontal = ('parcelas_original',)
    
    fieldsets = (
        ('Informações da Venda', {
            'fields': ('venda', 'tipo_renegociacao', 'status', 'responsavel')
        }),
        ('Dívida Original', {
            'fields': ('parcelas_original', 'valor_total_divida')
        }),
        ('Nova Negociação', {
            'fields': (
                'valor_desconto', 'percentual_desconto', 'valor_novo_total',
                'numero_novas_parcelas', 'data_primeira_parcela'
            )
        }),
        ('Controle ASAAS', {
            'fields': ('asaas_ids_cancelados', 'asaas_ids_novos'),
            'classes': ('collapse',)
        }),
        ('Observações e Datas', {
            'fields': ('observacoes', 'data_criacao', 'data_atualizacao', 'data_efetivacao')
        }),
    )

@admin.register(HistoricoContatoRetencao)
class HistoricoContatoRetencaoAdmin(admin.ModelAdmin):
    list_display = ('venda', 'tipo_contato', 'resultado', 'data_contato', 'responsavel', 'data_proxima_tentativa')
    list_filter = ('tipo_contato', 'resultado', 'data_contato')
    search_fields = ('venda__id', 'venda__lead__nome_completo', 'responsavel__username', 'observacoes')
    readonly_fields = ('data_contato',)
    
    fieldsets = (
        ('Informações do Contato', {
            'fields': ('venda', 'renegociacao', 'tipo_contato', 'resultado')
        }),
        ('Detalhes', {
            'fields': ('observacoes', 'responsavel', 'data_contato', 'data_proxima_tentativa')
        }),
    )

