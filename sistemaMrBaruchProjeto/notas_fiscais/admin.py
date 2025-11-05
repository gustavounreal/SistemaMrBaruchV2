from django.contrib import admin
from .models import NotaFiscal, ConfiguracaoFiscal


@admin.register(NotaFiscal)
class NotaFiscalAdmin(admin.ModelAdmin):
    list_display = ['id', 'numero_nf', 'venda', 'tipo', 'valor_servico', 'status', 'data_emissao', 'email_enviado']
    list_filter = ['status', 'tipo', 'email_enviado', 'data_criacao']
    search_fields = ['numero_nf', 'id_nf_asaas', 'venda__id', 'venda__cliente__lead__nome_completo']
    readonly_fields = ['data_criacao', 'data_emissao', 'data_atualizacao', 'data_cancelamento']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('venda', 'parcela', 'tipo', 'status')
        }),
        ('Dados da Nota Fiscal', {
            'fields': ('id_nf_asaas', 'numero_nf', 'serie_nf', 'codigo_verificacao', 'chave_acesso')
        }),
        ('Valores', {
            'fields': ('valor_servico', 'aliquota_iss', 'valor_iss', 'descricao_servico', 'codigo_servico_municipal')
        }),
        ('Documentos', {
            'fields': ('url_pdf', 'url_xml')
        }),
        ('E-mail', {
            'fields': ('email_enviado', 'data_envio_email', 'email_destinatario')
        }),
        ('Cancelamento', {
            'fields': ('data_cancelamento', 'motivo_cancelamento', 'cancelada_por'),
            'classes': ('collapse',)
        }),
        ('Controle', {
            'fields': ('tentativas_emissao', 'mensagem_erro', 'log_integracao'),
            'classes': ('collapse',)
        }),
        ('Datas', {
            'fields': ('data_criacao', 'data_emissao', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ConfiguracaoFiscal)
class ConfiguracaoFiscalAdmin(admin.ModelAdmin):
    list_display = ['razao_social', 'cnpj', 'regime_tributario', 'emissao_automatica']
    
    fieldsets = (
        ('Dados da Empresa', {
            'fields': ('cnpj', 'razao_social', 'nome_fantasia', 'inscricao_municipal', 'inscricao_estadual')
        }),
        ('Endereço', {
            'fields': ('cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'uf')
        }),
        ('Configurações Fiscais', {
            'fields': ('regime_tributario', 'aliquota_iss_padrao', 'codigo_servico_padrao', 'descricao_servico_padrao')
        }),
        ('Automações', {
            'fields': ('email_remetente', 'emissao_automatica', 'envio_automatico_email', 'prazo_cancelamento_horas')
        }),
    )
