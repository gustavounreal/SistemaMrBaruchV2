from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

app_name = 'accounts'

urlpatterns = [
    # ...existing urls...
    path('api/buscar-captador/<int:captador_id>/', views.buscar_captador, name='buscar_captador'),
    # Páginas
    path('login/', views.login_page, name='login'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('perfil-atendente/', views.perfil_atendente, name='perfil_atendente'),
    path('logout-session/', views.logout_session, name='logout_session'),

    # API de Autenticação
    path('api/auth/login/', views.login_api, name='login_api'),
    path('api/auth/register/', views.register_api, name='register_api'),
    path('api/auth/google/', views.google_auth, name='google_auth'),
    path('api/auth/logout/', views.logout_api, name='logout_api'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/profile/', views.profile_view, name='profile'),
]