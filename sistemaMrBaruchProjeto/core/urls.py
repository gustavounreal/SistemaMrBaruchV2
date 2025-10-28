from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
   path('painel_configuracoes/', views.painel_configuracoes, name='painel_configuracoes'),
   path('documentacao/', views.central_documentacao, name='central_documentacao'),
   path('documentacao/sistema/', views.documentacao_sistema, name='documentacao_sistema'),
   path('documentacao/jornadas/', views.documentacao_jornadas, name='documentacao_jornadas'),
   path('documentacao/jornada/lead/', views.documentacao, name='documentacao_lead'),
   path('documentacao/modulos/', views.documentacao_modulos, name='documentacao_modulos'),
   path('documentacao/tecnica/', views.documentacao_tecnica, name='documentacao_tecnica'),
   path('documentacao/modulo/comissoes/', views.doc_comissoes, name='doc_comissoes'),
   path('documentacao/modulo/relatorios/', views.doc_relatorios, name='doc_relatorios'),
   path('painel_configuracoes/grupos/adicionar/', views.adicionar_usuario_grupo, name='adicionar_usuario_grupo'),
   path('painel_configuracoes/grupos/remover/', views.remover_usuario_grupo, name='remover_usuario_grupo'),
   path('painel_configuracoes/grupos/usuario/<int:usuario_id>/', views.obter_grupos_usuario_ajax, name='obter_grupos_usuario_ajax'),
   
   # Webhook ASAAS
   path('webhook/asaas/', views.webhook_asaas, name='webhook_asaas'),
   
   # Logs de Webhooks
   path('webhook/logs/', views.webhook_logs, name='webhook_logs'),
   path('webhook/logs/<int:log_id>/', views.webhook_log_detalhe, name='webhook_log_detalhe'),
]