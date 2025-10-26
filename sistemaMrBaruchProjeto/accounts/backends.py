from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

UserModel = get_user_model()

class EmailBackend(ModelBackend):
    """
    Backend de autenticação que permite login com email
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Tenta encontrar o usuário por email
            user = UserModel.objects.get(
                Q(email__iexact=username) | 
                Q(username__iexact=username)
            )
        except UserModel.DoesNotExist:
            # Retorna None se não encontrar
            return None
        except UserModel.MultipleObjectsReturned:
            # Se houver múltiplos usuários com mesmo email, pega o primeiro
            user = UserModel.objects.filter(email=username).first()

        # Verifica a senha
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None