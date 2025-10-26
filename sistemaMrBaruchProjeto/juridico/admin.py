from django.contrib import admin
from .models import Contrato, DocumentoLegal


@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = ['numero_contrato', 'cliente', 'venda', 'status', 'data_geracao', 'data_assinatura']
    list_filter = ['status', 'assinatura_gov', 'data_geracao', 'data_assinatura']
    search_fields = ['numero_contrato', 'cliente__lead__nome_completo', 'cliente__lead__cpf']
    readonly_fields = ['data_criacao', 'data_atualizacao', 'numero_contrato']
    
    fieldsets = (
        ('Informações Principais', {
            'fields': ('venda', 'cliente', 'numero_contrato', 'status')
        }),
        ('Datas', {
            'fields': ('data_geracao', 'data_envio', 'data_assinatura', 'data_criacao', 'data_atualizacao')
        }),
        ('Assinaturas', {
            'fields': ('assinatura_gov', 'assinatura_manual')
        }),
        ('Arquivos', {
            'fields': ('arquivo_contrato', 'arquivo_assinado')
        }),
        ('Controle', {
            'fields': ('usuario_geracao', 'observacoes')
        }),
    )


@admin.register(DocumentoLegal)
class DocumentoLegalAdmin(admin.ModelAdmin):
    list_display = ['nome_documento', 'contrato', 'tipo', 'data_upload', 'usuario_upload']
    list_filter = ['tipo', 'data_upload']
    search_fields = ['nome_documento', 'contrato__numero_contrato']
    readonly_fields = ['data_upload']
