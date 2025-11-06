#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para verificar comissões faltantes de consultores e captadores
Execute: python verificar_comissoes_faltantes.py
"""
import os
import sys
import django

# Configurar o Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistemaMrBaruchProjeto.settings')
django.setup()

from vendas.models import Venda
from financeiro.models import PixEntrada, Comissao
from django.db.models import Sum
from decimal import Decimal

print("=" * 100)
print("🔍 VERIFICAÇÃO: COMISSÕES FALTANTES")
print("=" * 100)

# Buscar vendas com entrada PAGA
vendas_entrada_paga = Venda.objects.filter(
    status_pagamento_entrada='PAGO',
    valor_entrada__gt=0
).select_related('consultor', 'captador')

print(f"\n📊 Total de vendas com entrada PAGA: {vendas_entrada_paga.count()}")

for venda in vendas_entrada_paga:
    print(f"\n{'='*80}")
    print(f"🔸 Venda #{venda.id}")
    print(f"   Cliente: {venda.cliente.lead.nome_completo if hasattr(venda.cliente, 'lead') else 'N/A'}")
    print(f"   Valor Entrada: R$ {venda.valor_entrada:,.2f}")
    print(f"   Data: {venda.data_venda}")
    print(f"   Consultor: {venda.consultor.get_full_name() or venda.consultor.email}")
    if venda.captador:
        print(f"   Captador: {venda.captador.get_full_name() or venda.captador.email}")
    
    # Verificar comissões existentes
    comissoes_consultor = Comissao.objects.filter(
        venda=venda,
        tipo_comissao='CONSULTOR_ENTRADA'
    )
    
    comissoes_captador = Comissao.objects.filter(
        venda=venda,
        tipo_comissao='CAPTADOR_ENTRADA'
    )
    
    print(f"\n   📋 Comissões:")
    print(f"      Consultor: {comissoes_consultor.count()} comissão(ões)")
    for com in comissoes_consultor:
        print(f"         - R$ {com.valor_comissao:,.2f} ({com.percentual_comissao}%) - {com.status}")
    
    print(f"      Captador: {comissoes_captador.count()} comissão(ões)")
    for com in comissoes_captador:
        print(f"         - R$ {com.valor_comissao:,.2f} ({com.percentual_comissao}%) - {com.status}")
    
    # Verificar se há comissões faltantes
    if comissoes_consultor.count() == 0:
        print(f"\n   ⚠️  FALTANDO: Comissão de consultor!")
        # Calcular faturamento mensal
        mes = venda.data_venda.month if venda.data_venda else venda.data_criacao.month
        ano = venda.data_venda.year if venda.data_venda else venda.data_criacao.year
        
        faturamento_mes = Venda.objects.filter(
            consultor=venda.consultor,
            status_pagamento_entrada='PAGO',
            data_venda__year=ano,
            data_venda__month=mes
        ).aggregate(total=Sum('valor_entrada'))['total'] or Decimal('0')
        
        print(f"      Faturamento mensal: R$ {faturamento_mes:,.2f}")
        
        if faturamento_mes < Decimal('20000'):
            print(f"      Motivo: Faturamento abaixo de R$ 20.000 (regra atual)")
        
    if venda.captador and comissoes_captador.count() == 0:
        print(f"\n   ⚠️  FALTANDO: Comissão de captador!")
        comissao_esperada = (venda.valor_entrada * Decimal('3.0')) / Decimal('100')
        print(f"      Comissão esperada: R$ {comissao_esperada:,.2f} (3%)")

print("\n" + "=" * 100)
print("📊 RESUMO:")
print("=" * 100)

total_vendas = vendas_entrada_paga.count()
vendas_sem_comissao_consultor = 0
vendas_sem_comissao_captador = 0

for venda in vendas_entrada_paga:
    if not Comissao.objects.filter(venda=venda, tipo_comissao='CONSULTOR_ENTRADA').exists():
        vendas_sem_comissao_consultor += 1
    
    if venda.captador and not Comissao.objects.filter(venda=venda, tipo_comissao='CAPTADOR_ENTRADA').exists():
        vendas_sem_comissao_captador += 1

print(f"\nTotal de vendas com entrada paga: {total_vendas}")
print(f"Vendas SEM comissão de consultor: {vendas_sem_comissao_consultor}")
print(f"Vendas SEM comissão de captador: {vendas_sem_comissao_captador}")

if vendas_sem_comissao_consultor > 0:
    print(f"\n⚠️  {vendas_sem_comissao_consultor} vendas precisam de comissão de consultor!")
    print("   Execute: python corrigir_comissoes_consultores.py")

if vendas_sem_comissao_captador > 0:
    print(f"\n⚠️  {vendas_sem_comissao_captador} vendas precisam de comissão de captador!")
    print("   Solução: Verificar se o webhook está funcionando corretamente")

print("\n" + "=" * 100)
