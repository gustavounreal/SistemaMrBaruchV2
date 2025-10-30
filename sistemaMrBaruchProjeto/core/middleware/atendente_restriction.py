from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.http import JsonResponse


class AtendenteRestrictionMiddleware(MiddlewareMixin):
    """
    Middleware que restringe usuários do grupo 'atendente' a um conjunto limitado de rotas.
    Se um atendente tentar acessar outra rota, será redirecionado para a área de trabalho do atendente.

    Para requisições AJAX/JSON retorna 403 em vez de redirecionar.
    """

    def process_request(self, request):
        # Prefixos públicos que não devem ser bloqueados
        public_prefixes = [
            '/accounts/login/',
            '/accounts/api/auth/',
            '/accounts/logout-session/',
            '/accounts/api/',
           # '/admin/',
            '/static/',
            '/media/',
        ]

        # URLs permitidas para usuários do grupo 'atendente'
        allowed_paths = [
            '/atendimento/novo/',
            '/atendimento/lista/',
            '/atendimento/leads-pix/',
            '/atendimento/painel/',
            #'/atendimento/area-de-trabalho/',
            '/atendimento/perfil-atendente/',
            '/atendimento/api/',  # Permite todas as APIs de atendimento
            '/accounts/perfil-atendente/',
            '/accounts/logout-session/',
            '/clientes/',  # Permitir área do cliente
        ]

        # Permitir sempre paths públicos
        if any(request.path.startswith(p) for p in public_prefixes):
            return None

        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return None

        # Se o usuário for superuser ou do grupo 'admin', não aplicar restrição
        try:
            is_admin = user.is_superuser or user.groups.filter(name='admin').exists()
            if is_admin:
                return None
        except Exception:
            pass

        # Se o usuário for do grupo 'atendente', aplicar a restrição
        try:
            is_atendente = user.groups.filter(name='atendente').exists()
        except Exception:
            is_atendente = False

        if is_atendente:
            # permite se o path estiver explicitamente listado
            if any(request.path.startswith(p) for p in allowed_paths):
                return None

            # Para chamadas AJAX/JSON, devolve 403 em vez de redirecionar
            is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
            accepts_json = 'application/json' in request.META.get('HTTP_ACCEPT', '')
            if is_ajax or accepts_json or request.content_type == 'application/json':
                return JsonResponse({'detail': 'Acesso negado: atendentes somente acessam a área de trabalho.'}, status=403)

            # Redireciona para a área de trabalho do atendente
            try:
                target = reverse('atendimento:novo_atendimento')
            except Exception:
                target = '/atendimento/novo/'
            return redirect(target)

        return None
