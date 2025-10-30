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
            '/clientes/',  # Área do cliente sempre permitida
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
            print(f"[ConsultorRestriction] is_superuser: {user.is_superuser}, has_admin_group: {user.groups.filter(name='admin').exists()}")
            print(f"[ConsultorRestriction] is_admin: {is_admin}")
            if is_admin:
                print(f"[ConsultorRestriction] Liberado para admin: {request.path}")
                return None
        except Exception as e:
            print(f"[ConsultorRestriction] Erro ao verificar admin: {e}")
            pass

        # Se o usuário for do grupo 'cliente', permitir acesso apenas à área do cliente
        try:
            is_cliente = user.groups.filter(name='cliente').exists()
            print(f"[ConsultorRestriction] is_cliente: {is_cliente}")
            if is_cliente:
                # Clientes só podem acessar /clientes/area/ e rotas públicas
                if request.path.startswith('/clientes/'):
                    print(f"[ConsultorRestriction] Liberado para cliente: {request.path}")
                    return None
                # Se tentar acessar outra área, redireciona para área do cliente
                print(f"[ConsultorRestriction] Cliente tentando acessar área restrita, redirecionando...")
                return redirect('/clientes/area/')
        except Exception as e:
            print(f"[ConsultorRestriction] Erro ao verificar cliente: {e}")
            pass

        # Se o usuário for do grupo 'consultor', aplicar a restrição
        try:
            is_consultor = user.groups.filter(name='comercial1').exists()  # Atualizado de 'consultor' para 'comercial1'
            print(f"[ConsultorRestriction] is_consultor: {is_consultor}")
        except Exception as e:
            print(f"[ConsultorRestriction] Erro ao verificar consultor: {e}")
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
