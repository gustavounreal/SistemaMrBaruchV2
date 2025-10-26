from django.contrib.auth.models import Group

def is_funcionario(request):
    """
    Context processor para verificar se usuário é funcionário
    """
    if request.user.is_authenticated:
        return {'is_funcionario': request.user.groups.filter(name='funcionarios').exists()}
    return {'is_funcionario': False}