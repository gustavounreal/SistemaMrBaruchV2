from django.urls import path
from . import views

app_name = 'relatorios'

urlpatterns = [
    path('', views.painel_relatorios, name='painel_relatorios'),
    path('graficos/', views.dashboard_graficos, name='dashboard_graficos'),
    path('leads/', views.relatorio_leads, name='relatorio_leads'),
    path('vendas/', views.relatorio_vendas, name='relatorio_vendas'),
    path('comissoes/', views.relatorio_comissoes, name='relatorio_comissoes'),
    path('financeiro/', views.relatorio_financeiro, name='relatorio_financeiro'),
    path('exportar/<str:tipo>/', views.exportar_relatorio, name='exportar_relatorio'),
]
