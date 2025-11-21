"""
URLs do módulo asaas_sync
"""
from django.urls import path
from . import views

app_name = 'asaas_sync'

urlpatterns = [
    path('', views.dashboard_asaas_sync, name='dashboard'),
    path('clientes/', views.lista_clientes, name='lista_clientes'),
    path('clientes/<int:cliente_id>/', views.detalhes_cliente, name='detalhes_cliente'),
    path('clientes/<int:cliente_id>/atualizar/', views.atualizar_cliente, name='atualizar_cliente'),
    path('clientes/<int:cliente_id>/upload-documento/', views.upload_documento_cliente, name='upload_documento_cliente'),
    path('clientes/<int:cliente_id>/atualizar-telefone/', views.atualizar_telefone_cliente, name='atualizar_telefone_cliente'),
    path('documentos/<int:documento_id>/excluir/', views.excluir_documento_cliente, name='excluir_documento_cliente'),
    path('documentos/<int:documento_id>/download/', views.download_documento_cliente, name='download_documento_cliente'),
    path('cobrancas/', views.lista_cobrancas, name='lista_cobrancas'),
    path('sincronizar/', views.sincronizar_agora, name='sincronizar_agora'),
    path('sincronizar-alternativo/', views.sincronizar_alternativo, name='sincronizar_alternativo'),
    path('sincronizar-boletos-faltantes/', views.sincronizar_boletos_faltantes, name='sincronizar_boletos_faltantes'),
    path('baixar-dados-asaas/', views.baixar_dados_asaas, name='baixar_dados_asaas'),
    path('importar-json-limpo/', views.importar_json_limpo, name='importar_json_limpo'),
    path('status-operacao/<int:log_id>/', views.status_operacao, name='status_operacao'),
    path('validar/', views.validar_sincronizacao, name='validar_sincronizacao'),
    path('relatorio/', views.relatorio_completo, name='relatorio_completo'),
    path('exportar-clientes/', views.exportar_clientes_excel, name='exportar_clientes_excel'),
    path('exportar-cobrancas/', views.exportar_cobrancas_excel, name='exportar_cobrancas_excel'),
    path('exportar-completo/', views.exportar_clientes_com_boletos_excel, name='exportar_clientes_com_boletos_excel'),
    path('status-sincronizacao/<int:log_id>/', views.status_sincronizacao, name='status_sincronizacao'),
]
