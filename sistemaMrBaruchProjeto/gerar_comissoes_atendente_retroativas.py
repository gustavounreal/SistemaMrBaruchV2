#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para gerar comissões retroativas de atendentes
Execute: python gerar_comissoes_atendente_retroativas.py
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistemaMrBaruchProjeto.settings')
django.setup()

from financeiro.models import PixLevantamento
from comissoes.models import ComissaoLead
from comissoes.services import gerar_comissao_levantamento
from marketing.models import Lead

print("=" * 100)
print("🔧 GERANDO COMISSÕES RETROATIVAS DE ATENDENTES")
print("=" * 100)

# Buscar PIX Levantamentos pagos
pix_pagos = PixLevantamento.objects.filter(status_pagamento='pago')
print(f"\nTotal de PIX Levantamentos pagos: {pix_pagos.count()}")

comissoes_criadas = 0
comissoes_ja_existentes = 0
leads_sem_atendente = 0
erros = []

for pix in pix_pagos:
    lead = pix.lead
    
    # Verificar se já existe comissão para este lead
    comissao_existente = ComissaoLead.objects.filter(lead=lead).exists()
    
    if comissao_existente:
        comissoes_ja_existentes += 1
        continue
    
    # Verificar se o lead tem atendente
    if not lead.atendente:
        leads_sem_atendente += 1
        print(f"\n⚠️  Lead #{lead.id} ({lead.nome_completo}) não tem atendente vinculado")
        print(f"   PIX: #{pix.id} - R$ {pix.valor:.2f} - {pix.data_criacao.strftime('%d/%m/%Y')}")
        continue
    
    # Gerar comissão retroativa
    try:
        comissao = gerar_comissao_levantamento(lead, lead.atendente)
        if comissao:
            comissoes_criadas += 1
            print(f"\n✅ Comissão criada:")
            print(f"   Lead: {lead.nome_completo}")
            print(f"   Atendente: {lead.atendente.get_full_name() or lead.atendente.email}")
            print(f"   Valor: R$ {comissao.valor:.2f}")
            print(f"   PIX: #{pix.id} - R$ {pix.valor:.2f}")
    except Exception as e:
        erros.append({
            'lead_id': lead.id,
            'lead_nome': lead.nome_completo,
            'erro': str(e)
        })
        print(f"\n❌ Erro ao gerar comissão para Lead #{lead.id} ({lead.nome_completo}): {e}")

# RESUMO
print("\n\n" + "=" * 100)
print("📊 RESUMO:")
print("=" * 100)

print(f"\n✅ Comissões criadas: {comissoes_criadas}")
print(f"⏭️  Comissões já existentes: {comissoes_ja_existentes}")
print(f"⚠️  Leads sem atendente: {leads_sem_atendente}")

if erros:
    print(f"\n❌ Erros ({len(erros)}):")
    for erro in erros:
        print(f"   Lead #{erro['lead_id']} ({erro['lead_nome']}): {erro['erro']}")

# Verificar totais atualizados
print("\n📊 TOTAIS ATUALIZADOS:")
total_comissoes = ComissaoLead.objects.count()
print(f"Total de comissões de atendente: {total_comissoes}")

from decimal import Decimal
from django.db.models import Sum

valor_total = ComissaoLead.objects.aggregate(total=Sum('valor'))['total'] or Decimal('0')
print(f"Valor total: R$ {valor_total:.2f}")

print("\nPor status:")
for status in ['DISPONIVEL', 'AUTORIZADO', 'PAGO', 'CANCELADO']:
    count = ComissaoLead.objects.filter(status=status).count()
    valor = ComissaoLead.objects.filter(status=status).aggregate(total=Sum('valor'))['total'] or Decimal('0')
    print(f"  {status}: {count} - R$ {valor:.2f}")

print("\n" + "=" * 100)
print("✅ PROCESSO CONCLUÍDO!")
print("=" * 100)
