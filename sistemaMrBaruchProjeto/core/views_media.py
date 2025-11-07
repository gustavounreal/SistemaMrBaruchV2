"""
View personalizada para servir arquivos media
Resolve problema de redirect 302
"""
import os
import mimetypes
from django.http import FileResponse, Http404, HttpResponse
from django.conf import settings
from pathlib import Path


def serve_media(request, path):
    """
    Serve arquivos media diretamente sem redirect
    """
    # Constrói o caminho completo do arquivo
    file_path = Path(settings.MEDIA_ROOT) / path
    
    # Verifica se o arquivo existe
    if not file_path.exists() or not file_path.is_file():
        raise Http404("Arquivo não encontrado")
    
    # Detecta o tipo MIME
    content_type, encoding = mimetypes.guess_type(str(file_path))
    if content_type is None:
        content_type = 'application/octet-stream'
    
    # Abre e retorna o arquivo
    try:
        response = FileResponse(open(file_path, 'rb'), content_type=content_type)
        response['Content-Disposition'] = f'inline; filename="{file_path.name}"'
        return response
    except IOError:
        raise Http404("Erro ao ler arquivo")
