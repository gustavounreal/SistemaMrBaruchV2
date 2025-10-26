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
]

