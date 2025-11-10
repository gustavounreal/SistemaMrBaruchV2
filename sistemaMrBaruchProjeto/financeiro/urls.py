from django.urls import path
from . import views

app_name = 'financeiro'

urlpatterns = [
    # Dashboard Principal
    path('', views.dashboard_financeiro, name='dashboard'),
    
    # Retenção - Inadimplentes
    path('retencao/', views.painel_retencao, name='painel_retencao'),
    path('retencao/inadimplentes/', views.lista_inadimplentes, name='lista_inadimplentes'),
    path('retencao/renegociar/<int:venda_id>/', views.renegociar_divida, name='renegociar_divida'),
    path('retencao/historico/<int:venda_id>/', views.historico_negociacoes, name='historico_negociacoes'),
    
    # Financeiro - Entradas e Recebimentos
    path('entradas/', views.painel_entradas, name='painel_entradas'),
    path('entradas/diario/', views.entradas_diario, name='entradas_diario'),
    path('entradas/semanal/', views.entradas_semanal, name='entradas_semanal'),
    path('entradas/mensal/', views.entradas_mensal, name='entradas_mensal'),
    
    # Parcelas
    path('parcelas/', views.lista_parcelas, name='lista_parcelas'),
    path('parcelas/<int:parcela_id>/detalhes/', views.detalhes_parcela, name='detalhes_parcela'),
    path('parcelas/<int:parcela_id>/marcar-paga/', views.marcar_parcela_paga, name='marcar_parcela_paga'),
    path('parcelas/<int:parcela_id>/editar-data/', views.editar_data_parcela, name='editar_data_parcela'),
    path('parcelas/<int:parcela_id>/boleto/', views.imprimir_boleto_parcela, name='imprimir_boleto_parcela'),
    
    # Relatórios
    path('relatorios/inadimplencia/', views.relatorio_inadimplencia, name='relatorio_inadimplencia'),
    
    # Clientes Aptos para Liminar
    path('aptos-liminar/', views.lista_clientes_aptos_liminar, name='lista_aptos_liminar'),
]