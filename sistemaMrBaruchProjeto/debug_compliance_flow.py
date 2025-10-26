#!/usr/bin/env python
"""
Script de Debug: Fluxo Compliance → Painel de Vendas
Verifica se leads atribuídos aparecem corretamente no painel do consultor
"""

import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistemaMrBaruchProjeto.settings')
django.setup()

from django.contrib.auth.models import User
from marketing.models import Lead
from compliance.models import AnaliseCompliance
from financeiro.models import PixLevantamento

print("=" * 80)
print("🔍 DEBUG: FLUXO COMPLIANCE → PAINEL DE VENDAS")
print("=" * 80)

# 1. Listar todos os consultores
print("\n📋 1. CONSULTORES CADASTRADOS:")
print("-" * 80)
consultores = User.objects.filter(groups__name='comercial1')
if consultores.exists():
    for consultor in consultores:
        print(f"  ✓ {consultor.username} (ID: {consultor.id})")
        print(f"    Email: {consultor.email}")
        print(f"    Grupos: {', '.join(consultor.groups.values_list('name', flat=True))}")
else:
    print("  ⚠️ Nenhum consultor encontrado no grupo 'comercial1'")

# 2. Listar análises de compliance atribuídas
print("\n📋 2. ANÁLISES DE COMPLIANCE ATRIBUÍDAS:")
print("-" * 80)
analises = AnaliseCompliance.objects.filter(
    status='ATRIBUIDO'
).select_related('lead', 'consultor_atribuido')

if analises.exists():
    for analise in analises:
        print(f"\n  Lead #{analise.lead.id}: {analise.lead.nome_completo}")
        print(f"    Status Análise: {analise.status}")
        print(f"    Consultor: {analise.consultor_atribuido.username if analise.consultor_atribuido else 'Não atribuído'}")
        print(f"    Data Atribuição: {analise.data_atribuicao}")
        print(f"    Lead.passou_compliance: {analise.lead.passou_compliance}")
        print(f"    Lead.status: {analise.lead.status}")
        
        # Verificar PIX
        pix_pago = PixLevantamento.objects.filter(
            lead=analise.lead,
            status_pagamento='pago'
        )
        print(f"    PIX Pago: {'✓ Sim' if pix_pago.exists() else '✗ Não'}")
        if pix_pago.exists():
            for pix in pix_pago:
                print(f"      - R$ {pix.valor} (Criado em: {pix.data_criacao})")
else:
    print("  ⚠️ Nenhuma análise com status 'ATRIBUIDO' encontrada")

# 3. Simular query do painel de vendas para cada consultor
print("\n📋 3. SIMULAÇÃO DA QUERY DO PAINEL DE VENDAS:")
print("-" * 80)

for consultor in consultores:
    print(f"\n  👤 Consultor: {consultor.username}")
    print("  " + "-" * 76)
    
    # Query exata da view painel_leads_pagos
    leads_atribuidos_ids = AnaliseCompliance.objects.filter(
        consultor_atribuido=consultor
    ).values_list('lead_id', flat=True)
    
    print(f"    IDs de leads atribuídos: {list(leads_atribuidos_ids)}")
    
    leads = Lead.objects.filter(
        id__in=leads_atribuidos_ids,
        pix_levantamentos__status_pagamento='pago',
        passou_compliance=True,
        status__in=['APROVADO_COMPLIANCE', 'EM_NEGOCIACAO', 'QUALIFICADO']
    ).distinct()
    
    print(f"    Leads que apareceriam no painel: {leads.count()}")
    
    if leads.exists():
        for lead in leads:
            print(f"\n      ✓ Lead #{lead.id}: {lead.nome_completo}")
            print(f"        Status: {lead.status}")
            print(f"        Passou Compliance: {lead.passou_compliance}")
            
            pix = PixLevantamento.objects.filter(
                lead=lead,
                status_pagamento='pago'
            ).first()
            if pix:
                print(f"        PIX: R$ {pix.valor} (Pago)")
    else:
        print("      ⚠️ Nenhum lead apareceria no painel")
        
        # Diagnosticar por que não aparece
        print("\n      🔍 DIAGNÓSTICO:")
        for lead_id in leads_atribuidos_ids[:3]:  # Verificar primeiros 3
            try:
                lead = Lead.objects.get(id=lead_id)
                print(f"\n        Lead #{lead.id}:")
                
                # Verificar cada condição
                pix_pago = PixLevantamento.objects.filter(
                    lead=lead,
                    status_pagamento='pago'
                ).exists()
                print(f"          - PIX pago: {'✓' if pix_pago else '✗ FALHA'}")
                print(f"          - passou_compliance: {'✓' if lead.passou_compliance else '✗ FALHA'}")
                
                status_valido = lead.status in ['APROVADO_COMPLIANCE', 'EM_NEGOCIACAO', 'QUALIFICADO']
                print(f"          - status válido: {'✓' if status_valido else f'✗ FALHA (status atual: {lead.status})'}")
                
            except Lead.DoesNotExist:
                print(f"        Lead #{lead_id} não existe!")

# 4. Verificar todos os leads com PIX pago (independente de atribuição)
print("\n📋 4. TODOS OS LEADS COM PIX PAGO:")
print("-" * 80)
leads_com_pix = Lead.objects.filter(
    pix_levantamentos__status_pagamento='pago'
).distinct().select_related('captador', 'atendente')

print(f"  Total: {leads_com_pix.count()} leads com PIX pago\n")

for lead in leads_com_pix[:5]:  # Mostrar primeiros 5
    print(f"  Lead #{lead.id}: {lead.nome_completo}")
    print(f"    Status: {lead.status}")
    print(f"    Passou Compliance: {lead.passou_compliance}")
    
    # Verificar se está atribuído
    analise = AnaliseCompliance.objects.filter(lead=lead).first()
    if analise:
        print(f"    Atribuído a: {analise.consultor_atribuido.username if analise.consultor_atribuido else 'Não atribuído'}")
        print(f"    Status Análise: {analise.status}")
    else:
        print(f"    ⚠️ SEM ANÁLISE DE COMPLIANCE")
    print()

print("=" * 80)
print("✅ Debug concluído!")
print("=" * 80)
