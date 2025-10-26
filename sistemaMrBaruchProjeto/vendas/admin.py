from django.contrib import admin
from .models import MotivoRecusa, Servico, Venda, Parcela, PagamentoPIX, PreVenda, DocumentoVenda


@admin.register(MotivoRecusa)
class MotivoRecusaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'ativo', 'ordem', 'cor', 'data_criacao']
    list_filter = ['ativo', 'data_criacao']
    search_fields = ['nome', 'descricao']
    list_editable = ['ativo', 'ordem']
    ordering = ['ordem', 'nome']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome', 'descricao', 'ativo')
        }),
        ('Configurações de Exibição', {
            'fields': ('ordem', 'cor')
        }),
    )


@admin.register(Servico)
class ServicoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'tipo', 'preco_base', 'prazo_medio', 'ativo']
    list_filter = ['tipo', 'ativo']
    search_fields = ['nome', 'descricao']


@admin.register(PreVenda)
class PreVendaAdmin(admin.ModelAdmin):
    list_display = ['id', 'lead', 'status', 'servico_interesse', 'valor_proposto', 'data_criacao']
    list_filter = ['status', 'prazo_risco', 'data_criacao']
    search_fields = ['lead__nome_completo', 'observacoes_levantamento']
    raw_id_fields = ['lead', 'atendente', 'motivo_principal', 'perfil_emocional', 'motivo_recusa_principal']
    
    fieldsets = (
        ('Lead', {
            'fields': ('lead', 'atendente')
        }),
        ('Qualificação', {
            'fields': ('prazo_risco', 'motivo_principal', 'perfil_emocional')
        }),
        ('Proposta', {
            'fields': ('servico_interesse', 'valor_proposto', 'observacoes_levantamento')
        }),
        ('Status e Aceite', {
            'fields': ('status', 'aceite_cliente', 'motivo_recusa_principal', 'motivo_recusa')
        }),
    )


# Register your models here.
