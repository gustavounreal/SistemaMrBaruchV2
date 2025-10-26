from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth import login
from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger(__name__)

class JWTAuthMiddleware(MiddlewareMixin):
    """
    Middleware para autenticação híbrida (Sessão + JWT)
    """
    
    def process_request(self, request):
        print(f"=== JWT MIDDLEWARE EXECUTANDO ===")
        print(f"Path: {request.path}")
        print(f"Method: {request.method}")
        
        # Skip para paths públicos
        public_paths = ['/accounts/login/', '/accounts/api/auth/', '/admin/', '/static/', '/media/']
        if any(request.path.startswith(path) for path in public_paths):
            print(f"Path publico, pulando: {request.path}")
            return None
            
        # Se já tem uma sessão válida, mantém e não sobrescreve
        if hasattr(request, 'session') and '_auth_user_id' in request.session:
            print(f"Usando sessão existente (user_id: {request.session.get('_auth_user_id')})")
            # NÃO retornar aqui - deixar o AuthenticationMiddleware processar
            return None
            
        # Tenta autenticação via JWT
        try:
            jwt_auth = JWTAuthentication()
            header = jwt_auth.get_header(request)
            
            if header is not None:
                raw_token = jwt_auth.get_raw_token(header)
                validated_token = jwt_auth.get_validated_token(raw_token)
                user = jwt_auth.get_user(validated_token)
                
                if user and getattr(user, 'ativo', True):
                    # Garante que temos uma sessão antes de fazer login
                    if not hasattr(request, 'session'):
                        from django.contrib.sessions.backends.db import SessionStore
                        request.session = SessionStore()
                    
                    # Define o usuário e cria sessão
                    request.user = user
                    request._cached_user = user
                    user.backend = 'django.contrib.auth.backends.ModelBackend'
                    login(request, user)
                    print(f"Usuario autenticado via JWT: {user.email} (session_id: {request.session.session_key})")
                    return None
                    
        except Exception as e:
            print(f"Erro na autenticacao JWT: {str(e)}")
        
        print(f"=== FIM JWT MIDDLEWARE ===")
        return None