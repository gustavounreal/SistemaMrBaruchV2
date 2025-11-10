from django.urls import path
from . import views

app_name = 'juridico'

urlpatterns = [
    path('', views.dashboard_juridico, name='dashboard'),
    path('contratos/', views.lista_contratos, name='lista_contratos'),
    path('contratos/<int:contrato_id>/', views.detalhes_contrato, name='detalhes_contrato'),
    path('contratos/gerar/<int:venda_id>/', views.gerar_contrato, name='gerar_contrato'),
    path('contratos/<int:contrato_id>/atualizar-status/', views.atualizar_status_contrato, name='atualizar_status'),
    path('contratos/enviados/', views.painel_contratos_enviados, name='painel_contratos_enviados'),
    path('contratos/<int:contrato_id>/marcar-enviado/', views.marcar_contrato_enviado, name='marcar_contrato_enviado'),
    path('contratos/<int:contrato_id>/marcar-assinado/', views.marcar_contrato_assinado, name='marcar_contrato_assinado'),
    path('contratos/<int:contrato_id>/reenviar-boletos/', views.reenviar_boletos_asaas, name='reenviar_boletos_asaas'),
    path('contratos/<int:contrato_id>/download/', views.download_contrato, name='download_contrato'),
    path('contratos/<int:contrato_id>/boletos/', views.baixar_todos_boletos, name='baixar_todos_boletos'),
    
    # Distratos
    path('distratos/', views.painel_distratos, name='painel_distratos'),
    path('distratos/solicitar/<int:venda_id>/', views.solicitar_distrato, name='solicitar_distrato'),
    path('distratos/<int:distrato_id>/', views.detalhes_distrato, name='detalhes_distrato'),
    path('distratos/<int:distrato_id>/tentar-acordo/', views.tentar_acordo, name='tentar_acordo'),
    path('distratos/<int:distrato_id>/recusar-acordo/', views.recusar_acordo, name='recusar_acordo'),
    path('distratos/<int:distrato_id>/gerar-multa/', views.gerar_multa, name='gerar_multa'),
    path('distratos/<int:distrato_id>/marcar-multa-paga/', views.marcar_multa_paga, name='marcar_multa_paga'),
    path('distratos/<int:distrato_id>/enviar-juridico/', views.enviar_juridico, name='enviar_juridico'),
    path('distratos/multas-vencidas/', views.lista_multas_vencidas, name='lista_multas_vencidas'),
    
    # Processos Jurídicos
    path('processos/', views.painel_processos, name='painel_processos'),
    path('processos/<int:processo_id>/', views.detalhes_processo, name='detalhes_processo'),
    path('processos/<int:processo_id>/marcar-assinado/', views.marcar_processo_assinado, name='marcar_processo_assinado'),
    path('processos/<int:processo_id>/concluir/', views.concluir_processo, name='concluir_processo'),
    
    # Relatórios
    path('relatorios/processos/', views.relatorio_processos, name='relatorio_processos'),
    path('relatorios/distratos/', views.relatorio_distratos, name='relatorio_distratos'),
]
