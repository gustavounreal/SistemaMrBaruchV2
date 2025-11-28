from django.urls import path
from . import views

app_name = 'compliance'

urlpatterns = [
    # Painel principal
    path('painel/', views.painel_compliance, name='painel'),
    
    # Perfil
    path('perfil/', views.perfil_compliance, name='perfil_compliance'),
    
    # Análises
    path('analises/', views.lista_analises, name='lista_analises'),
    path('lead/<int:lead_id>/', views.detalhes_lead_compliance, name='detalhes_lead'),
    
    # APIs
    path('api/analisar/<int:analise_id>/', views.analisar_lead, name='analisar_lead'),
    path('api/atribuir/<int:analise_id>/', views.atribuir_consultor, name='atribuir_consultor'),
    path('api/reatribuir/<int:analise_id>/', views.reatribuir_consultor, name='reatribuir_consultor'),
    path('api/desatribuir/<int:analise_id>/', views.desatribuir_consultor, name='desatribuir_consultor'),
    path('api/desreprovar/<int:analise_id>/', views.desreprovar_lead, name='desreprovar_lead'),
    path('api/historico-recente/', views.api_historico_recente, name='api_historico_recente'),
    
    # Documentos de Levantamento
    path('api/documento-levantamento/<int:analise_id>/upload/', views.upload_documento_levantamento, name='upload_documento_levantamento'),
    path('api/documento-levantamento/<int:documento_id>/excluir/', views.excluir_documento_levantamento, name='excluir_documento_levantamento'),
    path('api/documento-levantamento/<int:documento_id>/download/', views.download_documento_levantamento, name='download_documento_levantamento'),
    
    # Gestão Pós-Venda (Sistema Antigo - ATENÇÃO GALERA DO MR BARUCH - por compatibilidade)
    path('gestao-pos-venda/', views.gestao_pos_venda_lista, name='gestao_pos_venda_lista'),
    path('gestao-pos-venda/<int:gestao_id>/', views.gestao_pos_venda_detalhes, name='gestao_pos_venda_detalhes'),
    path('api/gestao-pos-venda/<int:gestao_id>/acao/', views.acao_pos_venda, name='acao_pos_venda'),
    
    # === SISTEMA NOVO - GESTÃO PÓS-VENDA COMPLETA ===
    
    # Painel Principal
    path('pos-venda/', views.painel_pos_venda, name='painel_pos_venda'),
    
    # Gestão Detalhada de Venda
    path('pos-venda/<int:venda_id>/', views.gestao_pos_venda, name='gestao_pos_venda'),
    
    # Conferência de Cadastro
    path('pos-venda/<int:venda_id>/conferencia/', views.realizar_conferencia, name='realizar_conferencia'),
    path('pos-venda/<int:venda_id>/aprovar/', views.aprovar_conferencia, name='aprovar_conferencia'),
    path('pos-venda/<int:venda_id>/reprovar/', views.reprovar_conferencia, name='reprovar_conferencia'),
    path('pos-venda/<int:venda_id>/reabrir/', views.reabrir_conferencia, name='reabrir_conferencia'),
    path('pos-venda/<int:venda_id>/corrigir-status/', views.corrigir_status_pos_venda, name='corrigir_status_pos_venda'),
    path('pos-venda/<int:venda_id>/editar-dados/', views.editar_dados_venda, name='editar_dados_venda'),
    
    # Gestão de Documentos
    path('pos-venda/<int:venda_id>/documento/upload/', views.upload_documento, name='upload_documento'),
    path('pos-venda/<int:venda_id>/documento/<int:documento_id>/validar/', views.validar_documento, name='validar_documento'),
    path('pos-venda/<int:venda_id>/documento/adicionar/', views.adicionar_documento_extra, name='adicionar_documento_extra'),
    
    # Gestão de Contratos
    path('pos-venda/<int:venda_id>/contrato/gerar/', views.gerar_contrato, name='gerar_contrato'),
    path('pos-venda/<int:venda_id>/contrato/enviar/', views.enviar_contrato, name='enviar_contrato'),
    path('pos-venda/<int:venda_id>/contrato/visualizar/', views.visualizar_contrato, name='visualizar_contrato'),
    path('pos-venda/<int:venda_id>/contrato/upload-assinado/', views.upload_contrato_assinado, name='upload_contrato_assinado'),
    path('pos-venda/<int:venda_id>/contrato/validar-assinatura/', views.validar_assinatura, name='validar_assinatura'),
    
    # Relatórios de Auditoria
    path('relatorios/auditoria/', views.relatorio_auditoria, name='relatorio_auditoria'),
    path('relatorios/auditoria/exportar/', views.exportar_relatorio_auditoria, name='exportar_relatorio_auditoria'),
]
