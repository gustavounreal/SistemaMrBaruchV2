from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from core import views as core_views
from core.views_media import serve_media
from captadores import views as captadores_views

def home_view(request):
    """Redireciona a página inicial para o login"""
    return redirect('accounts:login')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('asaas-sync/', include('asaas_sync.urls', namespace='asaas_sync')),
    path('atendimento/', include('atendimento.urls', namespace='atendimento')),
    
    # Link curto público (antes do include de captadores para não conflitar)
    path('c/<str:codigo>', captadores_views.redirecionar_link_curto, name='link_curto'),
    
    path('captadores/', include('captadores.urls', namespace='captadores')),
    path('clientes/', include('clientes.urls', namespace='clientes')),
    path('compliance/', include('compliance.urls', namespace='compliance')),
    path('core/', include('core.urls', namespace='core')),
    path('comissoes/', include('comissoes.urls', namespace='comissoes')),
    path('relacionamento/', include('relacionamento.urls', namespace='relacionamento')),
    path('relatorios/', include('relatorios.urls', namespace='relatorios')),
    path('vendas/', include('vendas.urls', namespace='vendas')),
    path('marketing/', include('marketing.urls', namespace='marketing')),
    path('juridico/', include('juridico.urls', namespace='juridico')),
    path('financeiro/', include('financeiro.urls', namespace='financeiro')),
    path('notas-fiscais/', include('notas_fiscais.urls', namespace='notas_fiscais')),
    
    # Webhook ASAAS (rota direta sem prefixo)
    path('webhook/asaas/', core_views.webhook_asaas, name='webhook_asaas'),
    path('', include('distratos.urls')),
    
    path('', home_view, name='home'),
]

# Servir arquivos de mídia em desenvolvimento
if settings.DEBUG:
    # Usar view personalizada para evitar redirect 302
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve_media, name='media'),
    ]
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])