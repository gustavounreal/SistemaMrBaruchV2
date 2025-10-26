from django.urls import path
from . import views

app_name = 'comissoes'

urlpatterns = [
    path('', views.painel_comissoes, name='painel_comissoes'),
    path('leads/', views.painel_comissoes_leads, name='painel_comissoes_leads'),
    path('relatorio/', views.relatorio_comissoes, name='relatorio_comissoes'),
]
