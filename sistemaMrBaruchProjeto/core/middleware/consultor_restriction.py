from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.http import JsonResponse


class ConsultorRestrictionMiddleware(MiddlewareMixin):
    """
    Middleware que restringe usuários do grupo 'consultor' a um conjunto limitado de rotas.
    Consultores só podem acessar áreas relacionadas a pré-vendas e seus leads atribuídos.

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

            # URLs permitidas para usuários do grupo 'comercial1' (consultores)
        allowed_paths = [
            '/vendas/',
            '/vendas/painel-leads-pagos/',
            '/vendas/listar_vendas/',
            '/vendas/lista/',
            '/vendas/nova/',
            '/vendas/cadastro_venda_direta/',
            '/vendas/perfil_consultor/',
            '/vendas/perfil/',
            '/vendas/metricas/',
            '/vendas/pre-venda/',
            '/vendas/cadastro/',
            '/vendas/pix-entrada/',
            '/vendas/confirmacao/',
            '/compliance/api/lead/',
            '/accounts/perfil/',
            '/accounts/logout-session/',
            '/pos-venda/',
        ]
        # Log para debug dos paths
        print(f"[ConsultorRestriction] request.path: {request.path}")
        print(f"[ConsultorRestriction] allowed_paths: {allowed_paths}")

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

        # Se o usuário for do grupo 'consultor', aplicar a restrição
        try:
            is_consultor = user.groups.filter(name='comercial1').exists()  # Atualizado de 'consultor' para 'comercial1'
        except Exception:
            is_consultor = False

        if is_consultor:
            # Permitir TODA a área de vendas para consultores
            if request.path.startswith('/vendas/'):
                print(f"[ConsultorRestriction] Liberado para consultor (área vendas): {request.path}")
                return None
            
            # Outras áreas específicas permitidas
            other_allowed = [
                '/compliance/api/lead/',
                '/accounts/perfil/',
                '/accounts/logout-session/',
                '/pos-venda/',
            ]
            
            if any(request.path.startswith(p) for p in other_allowed):
                print(f"[ConsultorRestriction] Liberado para consultor: {request.path}")
                return None

            # Para chamadas AJAX/JSON, devolve 403 em vez de redirecionar
            is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
            accepts_json = 'application/json' in request.META.get('HTTP_ACCEPT', '')
            if is_ajax or accepts_json or request.content_type == 'application/json':
                return JsonResponse({'detail': 'Acesso negado: consultores somente acessam área autorizada.'}, status=403)

            # Redireciona para o painel de leads pagos (vendas)
            try:
                target = reverse('vendas:painel_leads_pagos')
            except Exception:
                target = '/vendas/'
            return redirect(target)

        return None
