from django.urls import path
from . import views

app_name = 'relatorios'

urlpatterns = [
    path('', views.painel_relatorios, name='painel_relatorios'),
    path('central/', views.painel_central, name='painel_central'),
    path('graficos/', views.dashboard_graficos, name='dashboard_graficos'),
    path('ranking/', views.ranking_geral, name='ranking_geral'),
    path('graficos/evolucao-leads/', views.grafico_evolucao_leads, name='grafico_evolucao_leads'),
    path('leads/', views.relatorio_leads, name='relatorio_leads'),
    path('vendas/', views.relatorio_vendas, name='relatorio_vendas'),
    path('comissoes/', views.relatorio_comissoes, name='relatorio_comissoes'),
    path('financeiro/', views.relatorio_financeiro, name='relatorio_financeiro'),
    path('kpis-comercial2/', views.dashboard_kpis_comercial2, name='dashboard_kpis_comercial2'),
    path('exportar/<str:tipo>/', views.exportar_relatorio, name='exportar_relatorio'),
]
