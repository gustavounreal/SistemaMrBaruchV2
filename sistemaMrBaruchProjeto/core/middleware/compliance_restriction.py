from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.http import JsonResponse


class ComplianceRestrictionMiddleware(MiddlewareMixin):
    """
    Middleware que restringe usuários do grupo 'compliance' a um conjunto limitado de rotas.
    Se um usuário compliance tentar acessar outra rota, será redirecionado para a área de trabalho do compliance.

    Para requisições AJAX/JSON retorna 403 em vez de redirecionar.
    """

    def process_request(self, request):
        # Prefixos públicos que não devem ser bloqueados
        public_prefixes = [
            '/accounts/login/',
            '/accounts/api/auth/',
            '/accounts/logout-session/',
            '/accounts/api/',
            '/static/',
            '/media/',
        ]

        # URLs permitidas para usuários do grupo 'compliance'
        allowed_paths = [
            '/compliance/',
            '/compliance/painel/',
            '/compliance/analises/',
            '/compliance/api/',
            '/compliance/lead/',
            '/compliance/gestao-pos-venda/',
            '/accounts/perfil/',
            '/accounts/logout-session/',
            '/juridico/',  # Acesso completo ao módulo jurídico (integração)
            '/juridico/api/',
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

        # Se o usuário for do grupo 'compliance', aplicar a restrição
        try:
            is_compliance = user.groups.filter(name='compliance').exists()
        except Exception:
            is_compliance = False

        if is_compliance:
            # permite se o path estiver explicitamente listado
            if any(request.path.startswith(p) for p in allowed_paths):
                return None

            # Para chamadas AJAX/JSON, devolve 403 em vez de redirecionar
            is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
            accepts_json = 'application/json' in request.META.get('HTTP_ACCEPT', '')
            if is_ajax or accepts_json or request.content_type == 'application/json':
                return JsonResponse({'detail': 'Acesso negado: compliance somente acessa área autorizada.'}, status=403)

            # Redireciona para a área de trabalho do compliance
            try:
                target = reverse('compliance:painel')
            except Exception:
                target = '/compliance/painel/'
            return redirect(target)

        return None
