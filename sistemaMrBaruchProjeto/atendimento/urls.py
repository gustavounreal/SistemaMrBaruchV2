from django.urls import path
from . import views
from accounts import views as accounts_views

app_name = 'atendimento'

urlpatterns = [
    
    path('novo/', views.novo_atendimento, name='novo_atendimento'),
    
    
       # APIs para etapas cadastro Lead
    path('api/autenticar/', views.api_autenticar_e_redirecionar, name='api_autenticar'),
    path('api/buscar-lead-cpf-cnpj/', views.buscar_lead_por_cpf_cnpj, name='buscar_lead_cpf_cnpj'),
    path('api/salvar-lead/', views.salvar_lead_api, name='salvar_lead_api'),
    path('api/salvar-lead-sem-levantamento/', views.salvar_lead_sem_levantamento, name='salvar_lead_sem_levantamento'),
    path('api/gerar-pix/<int:lead_id>/', views.gerar_pix_api, name='gerar_pix_api'),
    
    # Rotas auxiliares
    path('lista/', views.lista_atendimentos, name='lista_atendimentos'),
    path('webhook/pix/', views.webhook_pagamento_pix, name='webhook_pix'),
    path('leads-pix/', views.lista_leads_pix, name='lista_leads_pix'),
    path('painel/', views.painel_atendente, name='painel_atendente'),
    path('area-de-trabalho/', views.area_de_trabalho_atendente, name='area_de_trabalho_atendente'),
    # Alias para perfil do atendente (view está em accounts)
    path('perfil-atendente/', accounts_views.perfil_atendente, name='perfil_atendente'),

]