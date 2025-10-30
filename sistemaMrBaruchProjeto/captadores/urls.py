from django.urls import path
from . import views

app_name = 'captadores'

urlpatterns = [
    path('area/', views.area_captador, name='area_captador'),
]
