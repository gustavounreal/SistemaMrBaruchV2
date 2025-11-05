from django.urls import path
from . import views

app_name = 'notas_fiscais'

urlpatterns = [
    # Listagens
    path('pendentes/', views.lista_notas_pendentes, name='lista_pendentes'),
    path('emitidas/', views.lista_notas_emitidas, name='lista_emitidas'),
    path('todas/', views.lista_todas_notas, name='lista_todas'),
    
    # Ações
    path('emitir/<int:nf_id>/', views.emitir_nota_manual, name='emitir_manual'),
    path('reprocessar/<int:nf_id>/', views.reprocessar_nota_erro, name='reprocessar'),
    path('cancelar/<int:nf_id>/', views.cancelar_nota, name='cancelar'),
    path('reenviar-email/<int:nf_id>/', views.reenviar_email_nota, name='reenviar_email'),
    path('gerar-retroativas/', views.gerar_notas_retroativas, name='gerar_retroativas'),
    
    # Configuração
    path('configuracao/', views.configuracao_fiscal, name='configuracao_fiscal'),
    
    # Dashboard
    path('', views.dashboard_notas, name='dashboard'),
    path('relatorio/', views.relatorio_fiscal, name='relatorio_fiscal'),
]
