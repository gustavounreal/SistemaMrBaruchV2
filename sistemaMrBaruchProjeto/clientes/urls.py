from django.urls import path
from . import views

app_name = 'clientes'

urlpatterns = [
    # Área do Cliente
    path('area/', views.area_cliente, name='area_cliente'),
    path('boletos/', views.boletos_cliente, name='boletos_cliente'),
]
