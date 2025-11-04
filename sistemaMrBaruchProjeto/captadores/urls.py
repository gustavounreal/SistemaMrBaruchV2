from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'captadores'

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='captadores:area_captador', permanent=False), name='index'),
    path('area/', views.area_captador, name='area_captador'),
    path('materiais/upload/', views.upload_material, name='upload_material'),
    path('materiais/deletar/<int:material_id>/', views.deletar_material, name='deletar_material'),
    path('atualizar-dados/', views.atualizar_dados_captador, name='atualizar_dados_captador'),
]
