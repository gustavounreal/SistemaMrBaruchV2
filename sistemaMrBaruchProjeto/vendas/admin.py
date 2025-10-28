from django.contrib import admin
from .models import (
    MotivoRecusa, Servico, Venda, Parcela, PagamentoPIX, PreVenda, 
    DocumentoVenda, EstrategiaRepescagem, RepescagemLead, HistoricoRepescagem
)


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


@admin.register(EstrategiaRepescagem)
class EstrategiaRepescagemAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'motivo_recusa', 'ordem', 'ativo', 'data_criacao']
    list_filter = ['ativo', 'motivo_recusa', 'data_criacao']
    search_fields = ['titulo', 'descricao']
    list_editable = ['ordem', 'ativo']
    ordering = ['motivo_recusa', 'ordem']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('motivo_recusa', 'titulo', 'descricao')
        }),
        ('Configurações', {
            'fields': ('ordem', 'ativo')
        }),
    )


class HistoricoRepescagemInline(admin.TabularInline):
    model = HistoricoRepescagem
    extra = 0
    readonly_fields = ['data_interacao']
    fields = ['tipo_interacao', 'descricao', 'resultado', 'usuario', 'data_interacao']


@admin.register(RepescagemLead)
class RepescagemLeadAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'lead', 'status', 'motivo_recusa', 
        'consultor_repescagem', 'tentativas_contato', 'data_criacao'
    ]
    list_filter = ['status', 'motivo_recusa', 'condicoes_especiais_aplicadas', 'data_criacao']
    search_fields = ['lead__nome_completo', 'lead__telefone', 'observacoes_repescagem']
    raw_id_fields = ['lead', 'pre_venda', 'consultor_original', 'consultor_repescagem']
    readonly_fields = ['data_criacao', 'data_atualizacao', 'tentativas_contato']
    inlines = [HistoricoRepescagemInline]
    
    fieldsets = (
        ('Informações do Lead', {
            'fields': ('lead', 'pre_venda', 'motivo_recusa')
        }),
        ('Responsáveis', {
            'fields': ('consultor_original', 'consultor_repescagem')
        }),
        ('Status e Controle', {
            'fields': ('status', 'tentativas_contato', 'condicoes_especiais_aplicadas')
        }),
        ('Condições Especiais', {
            'fields': ('descricao_condicoes_especiais', 'novo_valor_total', 'novo_valor_entrada', 
                      'nova_quantidade_parcelas', 'novo_valor_parcela'),
            'classes': ('collapse',)
        }),
        ('Observações', {
            'fields': ('observacoes_consultor_original', 'observacoes_repescagem', 
                      'resposta_lead', 'proximos_passos')
        }),
        ('Datas', {
            'fields': ('data_criacao', 'data_atualizacao', 'data_primeiro_contato', 
                      'data_ultimo_contato', 'data_conclusao'),
            'classes': ('collapse',)
        }),
    )


@admin.register(HistoricoRepescagem)
class HistoricoRepescagemAdmin(admin.ModelAdmin):
    list_display = ['repescagem', 'tipo_interacao', 'usuario', 'data_interacao']
    list_filter = ['tipo_interacao', 'data_interacao']
    search_fields = ['repescagem__lead__nome_completo', 'descricao', 'resultado']
    raw_id_fields = ['repescagem', 'usuario']
    readonly_fields = ['data_interacao']


# Register your models here.
