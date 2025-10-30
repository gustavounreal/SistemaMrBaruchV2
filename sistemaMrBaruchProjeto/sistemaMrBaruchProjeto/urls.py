from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from core import views as core_views

def home_view(request):
    return HttpResponse('<h1>Sistema Mr. Baruch</h1><p><a href="/accounts/login/">Fazer Login</a></p>')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('atendimento/', include('atendimento.urls', namespace='atendimento')),
    path('compliance/', include('compliance.urls', namespace='compliance')),
    path('core/', include('core.urls', namespace='core')),
    path('comissoes/', include('comissoes.urls', namespace='comissoes')),
    path('relacionamento/', include('relacionamento.urls', namespace='relacionamento')),
    path('relatorios/', include('relatorios.urls', namespace='relatorios')),
    path('vendas/', include('vendas.urls', namespace='vendas')),
    path('marketing/', include('marketing.urls', namespace='marketing')),
    path('juridico/', include('juridico.urls', namespace='juridico')),
    path('financeiro/', include('financeiro.urls', namespace='financeiro')),
    
    # Webhook ASAAS (rota direta sem prefixo)
    path('webhook/asaas/', core_views.webhook_asaas, name='webhook_asaas'),
    path('', include('distratos.urls')),
    
    path('', home_view, name='home'),
    
    path('', home_view, name='home'),
]

# Servir arquivos de mídia em desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])