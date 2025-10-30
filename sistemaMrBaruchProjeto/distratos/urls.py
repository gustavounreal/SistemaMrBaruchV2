from django.urls import path
from django.views.generic import TemplateView

urlpatterns = [
    path('documentacao/distrato-juridico/', TemplateView.as_view(template_name='distratos/doc_distrato_juridico.html'), name='doc_distrato_juridico'),
]
