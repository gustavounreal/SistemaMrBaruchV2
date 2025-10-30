import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistemaMrBaruchProjeto.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()
print(f"✅ Modelo User: {User}")
print(f"✅ Manager disponível: {User.objects}")
print(f"✅ Total de usuários: {User.objects.count()}")
