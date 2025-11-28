"""
Script de teste para verificar consultores no grupo comercial1
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistemaMrBaruchProjeto.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

User = get_user_model()

print("\n" + "="*80)
print("TESTE: Verificando usuários no grupo comercial1")
print("="*80)

# 1. Verificar se o grupo comercial1 existe
try:
    grupo_comercial1 = Group.objects.get(name='comercial1')
    print(f"\n✅ Grupo 'comercial1' existe (ID: {grupo_comercial1.id})")
except Group.DoesNotExist:
    print("\n❌ ERRO: Grupo 'comercial1' NÃO EXISTE!")
    print("   Grupos disponíveis:")
    for g in Group.objects.all():
        print(f"   - {g.name}")
    exit(1)

# 2. Verificar usuários no grupo comercial1
consultores = User.objects.filter(
    groups__name='comercial1',
    is_active=True
)

print(f"\n📊 Total de usuários no grupo 'comercial1': {consultores.count()}")

if consultores.exists():
    print("\n👥 Consultores encontrados:")
    for consultor in consultores:
        print(f"   - ID: {consultor.id} | Username: {consultor.username} | Nome: {consultor.get_full_name() or '(sem nome)'} | Ativo: {consultor.is_active}")
else:
    print("\n⚠️  Nenhum consultor encontrado no grupo 'comercial1'")
    print("\n🔍 Verificando todos os grupos e usuários:")
    for grupo in Group.objects.all():
        usuarios = User.objects.filter(groups=grupo, is_active=True)
        print(f"\n   Grupo: {grupo.name} ({usuarios.count()} usuários)")
        for u in usuarios[:5]:  # Mostrar apenas 5 primeiros
            print(f"      - {u.username} ({u.get_full_name() or 'sem nome'})")

# 3. Testar o service
print("\n" + "="*80)
print("TESTE: ConsultorAtribuicaoService.listar_consultores_disponiveis()")
print("="*80)

from compliance.services import ConsultorAtribuicaoService

consultores_service = ConsultorAtribuicaoService.listar_consultores_disponiveis()
print(f"\n📊 Total retornado pelo service: {consultores_service.count()}")

if consultores_service.exists():
    print("\n👥 Consultores retornados pelo service:")
    for consultor in consultores_service:
        print(f"   - ID: {consultor.id} | Username: {consultor.username} | Nome: {consultor.get_full_name() or '(sem nome)'} | Leads Ativos: {consultor.leads_ativos}")
else:
    print("\n⚠️  Service retornou lista vazia")

print("\n" + "="*80)
