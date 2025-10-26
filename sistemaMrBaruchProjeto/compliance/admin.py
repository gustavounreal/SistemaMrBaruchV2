from django.contrib import admin
from .models import (
    AnaliseCompliance, 
    GestaoDocumentosPosVenda, 
    HistoricoAnaliseCompliance,
    ConferenciaVendaCompliance,
    DocumentoVendaCompliance,
    ContratoCompliance
)


@admin.register(AnaliseCompliance)
class AnaliseComplianceAdmin(admin.ModelAdmin):
    list_display = ['id', 'lead', 'classificacao', 'status', 'consultor_atribuido', 'data_criacao']
    list_filter = ['status', 'classificacao', 'data_criacao']
    search_fields = ['lead__nome_completo', 'lead__cpf_cnpj', 'lead__telefone']
    readonly_fields = ['data_criacao', 'data_atualizacao']
    raw_id_fields = ['lead', 'consultor_atribuido', 'analista_responsavel', 'pre_venda']
    
    fieldsets = (
        ('Lead', {
            'fields': ('lead', 'pre_venda')
        }),
        ('Análise', {
            'fields': ('classificacao', 'valor_divida_total', 'status', 'observacoes_analise', 'motivo_reprovacao')
        }),
        ('Atribuição', {
            'fields': ('consultor_atribuido', 'data_atribuicao', 'analista_responsavel')
        }),
        ('Datas', {
            'fields': ('data_criacao', 'data_analise', 'data_atualizacao')
        }),
    )


@admin.register(GestaoDocumentosPosVenda)
class GestaoDocumentosPosVendaAdmin(admin.ModelAdmin):
    list_display = ['id', 'pre_venda', 'status', 'cadastro_conferido', 'documentos_coletados', 'contrato_assinado']
    list_filter = ['status', 'cadastro_conferido', 'documentos_coletados', 'contrato_assinado']
    search_fields = ['pre_venda__lead__nome_completo', 'pre_venda__lead__cpf_cnpj']
    readonly_fields = ['data_criacao', 'data_atualizacao']
    raw_id_fields = ['analise_compliance', 'pre_venda', 'responsavel']


@admin.register(HistoricoAnaliseCompliance)
class HistoricoAnaliseComplianceAdmin(admin.ModelAdmin):
    list_display = ['id', 'analise', 'acao', 'usuario', 'data']
    list_filter = ['acao', 'data']
    search_fields = ['analise__lead__nome_completo', 'descricao']
    readonly_fields = ['data']
    raw_id_fields = ['analise', 'usuario']


# ============================================================================
# ADMIN PARA GESTÃO PÓS-VENDA
# ============================================================================

@admin.register(ConferenciaVendaCompliance)
class ConferenciaVendaComplianceAdmin(admin.ModelAdmin):
    list_display = ['id', 'venda', 'status', 'status_pagamento_entrada', 'analista', 'data_criacao']
    list_filter = ['status', 'status_pagamento_entrada', 'dados_cliente_conferidos', 'dados_venda_conferidos']
    search_fields = ['venda__id', 'venda__cliente__lead__nome_completo']
    readonly_fields = ['data_criacao', 'data_atualizacao', 'data_inicio_conferencia']
    raw_id_fields = ['venda', 'analista']
    
    fieldsets = (
        ('Venda e Status', {
            'fields': ('venda', 'analista', 'status', 'status_pagamento_entrada')
        }),
        ('Conferência do Cliente', {
            'fields': (
                'dados_cliente_conferidos',
                'nome_ok', 'cpf_ok', 'telefone_ok', 'email_ok', 'endereco_ok'
            )
        }),
        ('Conferência da Venda', {
            'fields': (
                'dados_venda_conferidos',
                'servico_ok', 'valores_ok', 'parcelas_ok', 'forma_pagamento_ok', 'datas_ok'
            )
        }),
        ('Observações', {
            'fields': ('observacoes_conferencia', 'pendencias', 'motivo_reprovacao')
        }),
        ('Documentos', {
            'fields': ('todos_documentos_ok',)
        }),
        ('Datas', {
            'fields': ('data_inicio_conferencia', 'data_aprovacao_conferencia', 'data_reprovacao', 
                      'data_criacao', 'data_atualizacao')
        }),
    )


@admin.register(DocumentoVendaCompliance)
class DocumentoVendaComplianceAdmin(admin.ModelAdmin):
    list_display = ['id', 'conferencia', 'tipo', 'status', 'obrigatorio', 'validado_por', 'data_upload']
    list_filter = ['tipo', 'status', 'obrigatorio', 'data_upload']
    search_fields = ['conferencia__venda__id', 'conferencia__venda__cliente__lead__nome_completo']
    readonly_fields = ['data_upload', 'data_validacao', 'data_criacao', 'data_atualizacao']
    raw_id_fields = ['conferencia', 'validado_por']
    
    fieldsets = (
        ('Documento', {
            'fields': ('conferencia', 'tipo', 'obrigatorio', 'arquivo', 'status')
        }),
        ('Validação', {
            'fields': ('observacao', 'motivo_rejeicao', 'validado_por', 'data_validacao')
        }),
        ('Datas', {
            'fields': ('data_upload', 'data_criacao', 'data_atualizacao')
        }),
    )


@admin.register(ContratoCompliance)
class ContratoComplianceAdmin(admin.ModelAdmin):
    list_display = ['numero_contrato', 'venda', 'status', 'tipo_assinatura', 'validado', 'data_geracao']
    list_filter = ['status', 'tipo_assinatura', 'validado', 'enviado_whatsapp', 'enviado_email']
    search_fields = ['numero_contrato', 'venda__id', 'venda__cliente__lead__nome_completo']
    readonly_fields = ['data_geracao', 'data_envio_whatsapp', 'data_envio_email', 
                      'data_assinatura', 'data_validacao', 'data_criacao', 'data_atualizacao']
    raw_id_fields = ['conferencia', 'venda', 'gerado_por', 'validado_por']
    
    fieldsets = (
        ('Contrato', {
            'fields': ('conferencia', 'venda', 'numero_contrato', 'status')
        }),
        ('Geração', {
            'fields': ('template_utilizado', 'arquivo_gerado', 'data_geracao', 'gerado_por')
        }),
        ('Envio WhatsApp', {
            'fields': ('enviado_whatsapp', 'data_envio_whatsapp', 'numero_whatsapp')
        }),
        ('Envio Email', {
            'fields': ('enviado_email', 'data_envio_email', 'email_destino')
        }),
        ('Assinatura', {
            'fields': ('tipo_assinatura', 'arquivo_assinado', 'data_assinatura', 'link_assinatura_gov')
        }),
        ('Validação', {
            'fields': ('validado', 'validado_por', 'data_validacao')
        }),
        ('Observações', {
            'fields': ('observacoes',)
        }),
        ('Datas', {
            'fields': ('data_criacao', 'data_atualizacao')
        }),
    )
