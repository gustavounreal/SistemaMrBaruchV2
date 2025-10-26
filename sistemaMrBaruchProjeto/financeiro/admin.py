from django.contrib import admin
from .models import Parcela, Comissao, PixLevantamento, PixEntrada, ClienteAsaas

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

