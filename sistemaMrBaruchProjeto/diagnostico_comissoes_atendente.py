#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para diagnosticar comissões de atendentes
Execute: python diagnostico_comissoes_atendente.py
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistemaMrBaruchProjeto.settings')
django.setup()

from financeiro.models import PixLevantamento
from comissoes.models import ComissaoLead
from django.db.models import Count, Sum
from decimal import Decimal

print("=" * 100)
print("🔍 DIAGNÓSTICO: COMISSÕES DE ATENDENTES")
print("=" * 100)

# 1. Verificar PIX Levantamentos pagos
print("\n📊 1. PIX LEVANTAMENTOS:")
print("-" * 100)

pix_pagos = PixLevantamento.objects.filter(status_pagamento='pago')
print(f"Total de PIX Levantamentos pagos: {pix_pagos.count()}")

if pix_pagos.exists():
    valor_total = pix_pagos.aggregate(total=Sum('valor'))['total'] or Decimal('0')
    print(f"Valor total: R$ {valor_total:,.2f}")
    
    print("\nDetalhes dos últimos 10:")
    for pix in pix_pagos.order_by('-data_criacao')[:10]:
        print(f"  - PIX #{pix.id}: R$ {pix.valor:,.2f} - {pix.lead.nome_completo} - {pix.data_criacao.strftime('%d/%m/%Y %H:%M')}")

# 2. Verificar Comissões de Atendente existentes
print("\n\n📊 2. COMISSÕES DE ATENDENTE:")
print("-" * 100)

comissoes_atendente = ComissaoLead.objects.all()
print(f"Total de comissões de atendente: {comissoes_atendente.count()}")

if comissoes_atendente.exists():
    valor_total = comissoes_atendente.aggregate(total=Sum('valor'))['total'] or Decimal('0')
    print(f"Valor total: R$ {valor_total:,.2f}")
    
    # Por status
    print("\nPor status:")
    for status in ['DISPONIVEL', 'AUTORIZADO', 'PAGO', 'CANCELADO']:
        count = comissoes_atendente.filter(status=status).count()
        valor = comissoes_atendente.filter(status=status).aggregate(total=Sum('valor'))['total'] or Decimal('0')
        print(f"  {status}: {count} comissão(ões) - R$ {valor:,.2f}")
    
    print("\nDetalhes das últimas 10:")
    for comissao in comissoes_atendente.order_by('-data_criacao')[:10]:
        print(f"  - Comissão #{comissao.id}: R$ {comissao.valor:.2f} - {comissao.atendente.get_full_name() or comissao.atendente.email}")
        print(f"    Lead: {comissao.lead.nome_completo} - Status: {comissao.status} - {comissao.data_criacao.strftime('%d/%m/%Y %H:%M')}")

# 3. Verificar PIX pagos SEM comissão
print("\n\n⚠️  3. PIX PAGOS SEM COMISSÃO:")
print("-" * 100)

pix_sem_comissao = []
for pix in pix_pagos:
    # Verificar se existe comissão para este lead
    comissao_existe = ComissaoLead.objects.filter(lead=pix.lead).exists()
    if not comissao_existe:
        pix_sem_comissao.append(pix)

print(f"Total de PIX pagos SEM comissão: {len(pix_sem_comissao)}")

if pix_sem_comissao:
    print(f"\n❌ PROBLEMA IDENTIFICADO: {len(pix_sem_comissao)} PIX levantamentos pagos não geraram comissão!")
    print("\nDetalhes:")
    for pix in pix_sem_comissao[:20]:
        print(f"\n  PIX #{pix.id}:")
        print(f"    Lead: {pix.lead.nome_completo}")
        print(f"    Valor: R$ {pix.valor:.2f}")
        print(f"    Data pagamento: {pix.data_criacao.strftime('%d/%m/%Y %H:%M')}")
        print(f"    Asaas Payment ID: {pix.asaas_payment_id}")
        
        # Verificar se o lead tem atendente
        if hasattr(pix.lead, 'usuario') and pix.lead.usuario:
            print(f"    Atendente: {pix.lead.usuario.get_full_name() or pix.lead.usuario.email}")
        else:
            print(f"    ⚠️  Lead SEM atendente vinculado!")

# 4. Análise do modelo Lead
print("\n\n📊 4. ANÁLISE DOS LEADS:")
print("-" * 100)

from marketing.models import Lead

leads_com_pix_pago = Lead.objects.filter(pix_levantamentos__status_pagamento='pago').distinct()
print(f"Leads com PIX pago: {leads_com_pix_pago.count()}")

leads_sem_atendente = leads_com_pix_pago.filter(atendente__isnull=True)
print(f"Leads com PIX pago SEM atendente: {leads_sem_atendente.count()}")

if leads_sem_atendente.exists():
    print("\n⚠️  Leads sem atendente vinculado:")
    for lead in leads_sem_atendente[:10]:
        pix_count = lead.pix_levantamentos.filter(status_pagamento='pago').count()
        print(f"  - Lead #{lead.id}: {lead.nome_completo} - {pix_count} PIX pago(s)")

# 5. Verificar campo de atendente no Lead
print("\n\n📊 5. CAMPO DE ATENDENTE NO MODELO LEAD:")
print("-" * 100)

# Verificar qual campo armazena o atendente
print("Campos do modelo Lead relacionados a usuário:")
for field in Lead._meta.get_fields():
    if 'user' in field.name.lower() or 'atendente' in field.name.lower():
        print(f"  - {field.name} ({type(field).__name__})")

# 6. RESUMO E RECOMENDAÇÕES
print("\n\n" + "=" * 100)
print("📊 RESUMO:")
print("=" * 100)

print(f"\n✅ PIX Levantamentos pagos: {pix_pagos.count()}")
print(f"✅ Comissões de atendente criadas: {comissoes_atendente.count()}")
print(f"❌ PIX pagos SEM comissão: {len(pix_sem_comissao)}")

if len(pix_sem_comissao) > 0:
    valor_perdido = Decimal('0.50') * len(pix_sem_comissao)
    print(f"\n⚠️  VALOR EM COMISSÕES NÃO GERADAS: R$ {valor_perdido:.2f}")
    
    print("\n🔧 POSSÍVEIS CAUSAS:")
    if leads_sem_atendente.count() > 0:
        print(f"  1. {leads_sem_atendente.count()} leads não têm atendente vinculado")
    print("  2. Webhook pode não estar gerando comissão automaticamente")
    print("  3. Campo de atendente pode estar incorreto")
    
    print("\n💡 SOLUÇÃO:")
    print("  Execute: python gerar_comissoes_atendente_retroativas.py")

print("\n" + "=" * 100)
