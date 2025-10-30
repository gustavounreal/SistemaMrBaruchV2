from django.shortcuts import redirect
from django.urls import reverse


class Comercial2RedirectMiddleware:
    """Redirect authenticated users in group 'comercial2' to the Comercial 2 panel.

    Rules:
    - Only redirect authenticated users who belong to the group 'comercial2'.
    - Only redirect from specific paths (/, /dashboard/, /vendas/) - not everywhere
    - Do not redirect if the request path is already under /vendas/comercial2/.
    - Skip for admin, static/media files, API endpoints and AJAX requests.
    - Respect a `next` parameter (do not override explicit redirects).
    """

    EXEMPT_PATH_PREFIXES = (
        '/static/',
        '/media/',
        '/admin/',
        '/api/',
        '/accounts/',
        '/relatorios/',      # Permitir acesso a relatórios
        '/core/',            # Permitir documentação e configurações
        '/compliance/',      # Permitir ver histórico quando lead volta
        '/vendas/comercial2', 
        '/clientes/',        
    )
    
    # Apenas redirecionar nestes paths específicos (login/raiz)
    REDIRECT_PATHS = ['/', '/dashboard/', '/vendas/']

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Proceed normally if not authenticated
        user = getattr(request, 'user', None)
        path = request.path

        try:
            # Quick exemptions
            for prefix in self.EXEMPT_PATH_PREFIXES:
                if path.startswith(prefix):
                    return self.get_response(request)

            if user and user.is_authenticated:
                # Avoid redirecting AJAX
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return self.get_response(request)

                # Check group membership
                try:
                    if user.groups.filter(name='comercial2').exists():
                        # Respect explicit next param
                        if request.GET.get('next'):
                            return self.get_response(request)

                        # MUDANÇA: Só redirecionar se estiver em paths específicos
                        if path in self.REDIRECT_PATHS:
                            return redirect('/vendas/comercial2/')
                except Exception:
                    # If something fails, don't block the request
                    pass

        except Exception:
            # Fail-open: ensure middleware doesn't break requests
            pass

        return self.get_response(request)
