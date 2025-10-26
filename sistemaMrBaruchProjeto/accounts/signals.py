from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

User = get_user_model()


@receiver(post_save, sender=User)
def add_user_to_clientes_group(sender, instance, created, **kwargs):
    """Adiciona novos usuários ao grupo 'clientes' por padrão."""
    if not created:
        return

    try:
        group, _ = Group.objects.get_or_create(name='clientes')
        instance.groups.add(group)
    except Exception:
        # Falha silenciosa; evita quebrar o fluxo de criação de usuário
        pass
