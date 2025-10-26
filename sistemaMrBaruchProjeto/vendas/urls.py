from django.urls import path
from . import views

app_name = 'vendas'

urlpatterns = [
    # Painel principal para consultores (leads com PIX pago)
    path('', views.painel_leads_pagos, name='painel_leads_pagos'),
    path('painel-leads-pagos/', views.painel_leads_pagos, name='painel_leads_pagos_alt'),
    
    # Cadastro direto de venda (sem pré-venda)
    path('nova/', views.cadastro_venda_direta, name='cadastro_venda_direta'),
    
    # Pré-venda (primeira etapa)
    path('pre-venda/iniciar/<int:lead_id>/', views.iniciar_pre_venda, name='iniciar_pre_venda'),
    path('pre-venda/<int:pre_venda_id>/', views.detalhes_pre_venda, name='detalhes_pre_venda'),
    
    # Aceite do cliente (segunda etapa)
    path('pre-venda/<int:pre_venda_id>/aceite/', views.registrar_aceite, name='registrar_aceite'),
    
    # Cadastro completo da venda (terceira etapa)
    path('cadastro/<int:pre_venda_id>/', views.cadastro_venda, name='cadastro_venda'),
    
    # Confirmação de venda cadastrada
    path('<int:venda_id>/confirmacao/', views.confirmacao_venda, name='confirmacao_venda'),
    
    # Exibir PIX da entrada
    path('<int:venda_id>/pix-entrada/', views.exibir_pix_entrada, name='exibir_pix_entrada'),
    
    # Listagem e detalhes de vendas concluídas
    path('lista/', views.listar_vendas, name='listar_vendas'),
    path('<int:venda_id>/', views.detalhes_venda, name='detalhes_venda'),

    # Perfil do consultor (comercial1)
    path('perfil/', views.perfil_consultor, name='perfil_consultor'),
    
    # Painel de métricas do consultor
    path('metricas/', views.painel_metricas_consultor, name='painel_metricas_consultor'),
    
    # Admin: Gerar comissões retroativas
    path('admin/gerar-comissoes-entradas/', views.gerar_comissoes_entradas_pagas, name='gerar_comissoes_entradas_pagas'),
]
