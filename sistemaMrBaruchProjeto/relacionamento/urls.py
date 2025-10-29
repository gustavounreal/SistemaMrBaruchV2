from django.urls import path
from . import views

app_name = 'relacionamento'

urlpatterns = [
    # Painel principal
    path('', views.painel_relacionamento, name='painel_relacionamento'),
    
    # Interações
    path('interacoes/', views.lista_interacoes, name='lista_interacoes'),
    path('interacoes/nova/', views.nova_interacao, name='nova_interacao'),
    path('interacoes/<int:pk>/', views.detalhe_interacao, name='detalhe_interacao'),
    
    # Pesquisas de Satisfação
    path('pesquisas/', views.pesquisas_satisfacao, name='pesquisas_satisfacao'),
    path('pesquisas/nova/', views.nova_pesquisa, name='nova_pesquisa'),
    
    # Indicações
    path('indicacoes/', views.indicacoes, name='indicacoes'),
    path('indicacoes/nova/', views.nova_indicacao, name='nova_indicacao'),
    
    # Programa de Fidelidade
    path('fidelidade/', views.programa_fidelidade, name='programa_fidelidade'),
    path('fidelidade/<int:cliente_id>/', views.detalhe_fidelidade, name='detalhe_fidelidade'),
]
