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
    path('cobrancas/', views.lista_cobrancas, name='lista_cobrancas'),
    path('sincronizar/', views.sincronizar_agora, name='sincronizar_agora'),
    path('sincronizar-alternativo/', views.sincronizar_alternativo, name='sincronizar_alternativo'),
    path('relatorio/', views.relatorio_completo, name='relatorio_completo'),
]
