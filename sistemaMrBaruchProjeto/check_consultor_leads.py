#!/usr/bin/env python
"""
Verificação: Consultor Logado e Leads Atribuídos
Identifica qual consultor está logado (user_id: 3) e verifica seus leads
"""

import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistemaMrBaruchProjeto.settings')

# Configurar Django sem verificar dependências
import django
from django.conf import settings
settings.configure(
    DEBUG=True,
    DATABASES={
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(os.path.dirname(__file__), 'db.sqlite3'),
        }
    },
    INSTALLED_APPS=[
        'django.contrib.contenttypes',
        'django.contrib.auth',
        'accounts',
        'marketing',
        'compliance',
        'vendas',
        'financeiro',
    ],
    USE_TZ=True,
)
django.setup()

from django.contrib.auth import get_user_model
from marketing.models import Lead
from compliance.models import AnaliseCompliance
from financeiro.models import PixLevantamento

User = get_user_model()

print("=" * 100)
print("🔍 VERIFICAÇÃO: CONSULTOR LOGADO E LEADS ATRIBUÍDOS")
print("=" * 100)

# 1. Identificar o usuário logado (user_id: 3 do log)
print("\n📋 1. USUÁRIO LOGADO (user_id: 3):")
print("-" * 100)

try:
    usuario_logado = User.objects.get(id=3)
    print(f"  ✓ Username: {usuario_logado.username}")
    print(f"    Nome: {usuario_logado.get_full_name() or '(não definido)'}")
    print(f"    Email: {usuario_logado.email}")
    print(f"    Superuser: {usuario_logado.is_superuser}")
    print(f"    Staff: {usuario_logado.is_staff}")
    print(f"    Grupos: {', '.join(usuario_logado.groups.values_list('name', flat=True))}")
except User.DoesNotExist:
    print("  ✗ Usuário com ID 3 não encontrado!")
    sys.exit(1)

# 2. Verificar se é consultor
print("\n📋 2. VERIFICAÇÃO DE PERMISSÕES:")
print("-" * 100)

is_consultor = usuario_logado.groups.filter(name='comercial1').exists()
is_admin = usuario_logado.is_superuser or usuario_logado.groups.filter(name='admin').exists()

print(f"  É consultor (comercial1): {'✓ SIM' if is_consultor else '✗ NÃO'}")
print(f"  É admin: {'✓ SIM' if is_admin else '✗ NÃO'}")

# 3. Buscar análises de compliance atribuídas
print("\n📋 3. ANÁLISES DE COMPLIANCE ATRIBUÍDAS AO USUÁRIO:")
print("-" * 100)

analises = AnaliseCompliance.objects.filter(
    consultor_atribuido=usuario_logado
).select_related('lead').order_by('-data_atribuicao')

print(f"  Total de análises atribuídas: {analises.count()}\n")

if analises.exists():
    for i, analise in enumerate(analises, 1):
        lead = analise.lead
        print(f"  {i}. Lead #{lead.id}: {lead.nome_completo}")
        print(f"     Status Análise: {analise.get_status_display()}")
        print(f"     Data Atribuição: {analise.data_atribuicao}")
        print(f"     Lead.passou_compliance: {lead.passou_compliance}")
        print(f"     Lead.status: {lead.status}")
        
        # Verificar PIX
        pix_pago = PixLevantamento.objects.filter(
            lead=lead,
            status_pagamento='pago'
        ).exists()
        print(f"     PIX pago: {'✓ SIM' if pix_pago else '✗ NÃO'}")
        
        # Verificar se passaria no filtro da view
        passaria = (
            pix_pago and
            lead.passou_compliance and
            lead.status in ['APROVADO_COMPLIANCE', 'EM_NEGOCIACAO', 'QUALIFICADO']
        )
        print(f"     ✅ Apareceria no painel: {'SIM' if passaria else 'NÃO'}")
        
        if not passaria:
            print(f"     ⚠️ MOTIVO:")
            if not pix_pago:
                print(f"        - Sem PIX pago")
            if not lead.passou_compliance:
                print(f"        - passou_compliance = False")
            if lead.status not in ['APROVADO_COMPLIANCE', 'EM_NEGOCIACAO', 'QUALIFICADO']:
                print(f"        - Status inválido: {lead.status}")
        print()
else:
    print("  ⚠️ Nenhuma análise atribuída a este usuário!")

# 4. Simular a query exata da view
print("\n📋 4. SIMULAÇÃO DA QUERY DA VIEW painel_leads_pagos:")
print("-" * 100)

# Query 1: Buscar IDs dos leads atribuídos
leads_atribuidos_ids = AnaliseCompliance.objects.filter(
    consultor_atribuido=usuario_logado
).values_list('lead_id', flat=True)

print(f"  IDs de leads atribuídos: {list(leads_atribuidos_ids)}\n")

# Query 2: Filtrar leads que aparecem no painel
leads_painel = Lead.objects.filter(
    id__in=leads_atribuidos_ids,
    pix_levantamentos__status_pagamento='pago',
    passou_compliance=True,
    status__in=['APROVADO_COMPLIANCE', 'EM_NEGOCIACAO', 'QUALIFICADO']
).distinct()

print(f"  ✅ Leads que apareceriam no painel: {leads_painel.count()}\n")

if leads_painel.exists():
    for lead in leads_painel:
        print(f"    - Lead #{lead.id}: {lead.nome_completo} (Status: {lead.status})")
else:
    print("    ⚠️ Nenhum lead apareceria no painel com os filtros da view")

# 5. Listar TODOS os leads com PIX pago (para comparação)
print("\n📋 5. TODOS OS LEADS COM PIX PAGO (independente de atribuição):")
print("-" * 100)

todos_leads_pix = Lead.objects.filter(
    pix_levantamentos__status_pagamento='pago'
).distinct().order_by('-data_cadastro')

print(f"  Total: {todos_leads_pix.count()} leads com PIX pago\n")

for lead in todos_leads_pix[:10]:  # Mostrar primeiros 10
    print(f"  Lead #{lead.id}: {lead.nome_completo}")
    print(f"    Status: {lead.status}")
    print(f"    passou_compliance: {lead.passou_compliance}")
    
    # Verificar atribuição
    analise = AnaliseCompliance.objects.filter(lead=lead).first()
    if analise:
        if analise.consultor_atribuido:
            print(f"    Atribuído a: {analise.consultor_atribuido.username} (ID: {analise.consultor_atribuido.id})")
        else:
            print(f"    ⚠️ Análise existe mas SEM consultor atribuído")
        print(f"    Status Análise: {analise.get_status_display()}")
    else:
        print(f"    ⚠️ SEM análise de compliance")
    print()

print("=" * 100)
print("✅ Verificação concluída!")
print("=" * 100)
