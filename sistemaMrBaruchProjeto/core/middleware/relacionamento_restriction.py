from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.http import JsonResponse


class RelacionamentoRestrictionMiddleware(MiddlewareMixin):
    """
    Middleware que restringe usuários do grupo 'relacionamento' a um conjunto limitado de rotas.
    Permite acesso apenas a:
    - /relacionamento/ (área de relacionamento)
    - /financeiro/retencao/ (área de retenção financeira)
    
    Se um usuário do relacionamento tentar acessar outra rota, será redirecionado.
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

        # URLs permitidas para usuários do grupo 'relacionamento'
        allowed_paths = [
            '/relacionamento/',  # Toda área de relacionamento
            '/financeiro/retencao/',  # Área de retenção no financeiro
            '/accounts/perfil/',
            '/accounts/logout-session/',
        ]

        # Permitir sempre paths públicos
        if any(request.path.startswith(p) for p in public_prefixes):
            return None

        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return None

        # Se o usuário for superuser ou do grupo 'admin', não aplicar restrição
        if user.is_superuser or user.groups.filter(name__in=['admin', 'Admin']).exists():
            return None

        # Verificar se o usuário pertence ao grupo 'relacionamento'
        is_relacionamento = user.groups.filter(name__in=['relacionamento', 'Relacionamento']).exists()
        
        if not is_relacionamento:
            return None

        # Se for do relacionamento, verificar se está acessando uma rota permitida
        if any(request.path.startswith(allowed_path) for allowed_path in allowed_paths):
            return None

        # Se chegou aqui, é um usuário do relacionamento tentando acessar área não autorizada
        
        # Para requisições AJAX/JSON, retornar erro 403
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
           request.headers.get('Accept', '').startswith('application/json'):
            return JsonResponse({
                'error': 'Acesso negado',
                'message': 'Você não tem permissão para acessar esta área. Apenas áreas de Relacionamento e Retenção Financeira estão disponíveis.'
            }, status=403)

        # Para requisições normais, redirecionar para o painel do relacionamento
        return redirect('/relacionamento/')
