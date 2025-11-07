from django.urls import path
from . import views
from .views_gestao import (
    painel_gestao_comissoes,
    autorizar_comissao_view,
    processar_pagamento_view,
    cancelar_comissao_view,
    dashboard_comissoes,
    relatorio_usuario
    , painel_transferencias_comissoes
)

app_name = 'comissoes'

urlpatterns = [
    # URLs antigas (manter compatibilidade)
    path('', views.painel_comissoes, name='painel_comissoes'),
    path('leads/', views.painel_comissoes_leads, name='painel_comissoes_leads'),
    path('relatorio/', views.relatorio_comissoes, name='relatorio_comissoes'),
    
    # URLs de Gestão (novo sistema)
    path('gestao/', painel_gestao_comissoes, name='painel_gestao'),
    path('gestao/dashboard/', dashboard_comissoes, name='dashboard'),
    path('gestao/<str:tipo>/<int:comissao_id>/autorizar/', autorizar_comissao_view, name='autorizar'),
    path('gestao/<str:tipo>/<int:comissao_id>/pagar/', processar_pagamento_view, name='pagar'),
    path('gestao/<str:tipo>/<int:comissao_id>/cancelar/', cancelar_comissao_view, name='cancelar'),
    path('gestao/relatorio/<str:tipo>/<int:user_id>/', relatorio_usuario, name='relatorio_usuario'),
        path('gestao/transferencias/', painel_transferencias_comissoes, name='painel_transferencias'),
]
