#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para Corrigir Comissões de Consultores e Inconsistências
Execute: python corrigir_comissoes_consultores.py
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
from datetime import datetime

print("=" * 100)
print("🔧 CORREÇÃO: COMISSÕES DE CONSULTORES E INCONSISTÊNCIAS")
print("=" * 100)

# ==========================================
# 1. CORRIGIR INCONSISTÊNCIAS DE STATUS
# ==========================================
print("\n📝 1. CORRIGINDO INCONSISTÊNCIAS DE STATUS:")
print("-" * 100)

inconsistencias_corrigidas = 0
for pix in PixEntrada.objects.filter(status_pagamento='pago'):
    if pix.venda.status_pagamento_entrada != 'PAGO':
        venda = pix.venda
        print(f"\n  Corrigindo Venda #{venda.id}:")
        print(f"    Status Anterior: '{venda.status_pagamento_entrada}'")
        print(f"    Status Novo: 'PAGO'")
        print(f"    PixEntrada: #{pix.id} - R$ {pix.valor:,.2f}")
        
        venda.status_pagamento_entrada = 'PAGO'
        venda.save(update_fields=['status_pagamento_entrada'])
        
        inconsistencias_corrigidas += 1

print(f"\n✅ {inconsistencias_corrigidas} inconsistência(s) corrigida(s)")

# ==========================================
# 2. GERAR COMISSÕES DE CONSULTORES
# ==========================================
print("\n\n📊 2. GERANDO COMISSÕES DE CONSULTORES:")
print("-" * 100)

# Buscar todas as vendas com entrada PAGA
vendas_entrada_paga = Venda.objects.filter(
    status_pagamento_entrada='PAGO',
    valor_entrada__gt=0
).select_related('consultor', 'captador')

print(f"\nVendas com entrada paga: {vendas_entrada_paga.count()}")

comissoes_consultor_criadas = 0
comissoes_ja_existentes = 0
erros = []

for venda in vendas_entrada_paga:
    try:
        # Verificar se já existe comissão de consultor para esta venda
        comissao_existente = Comissao.objects.filter(
            venda=venda,
            tipo_comissao='CONSULTOR_ENTRADA'
        ).first()
        
        if comissao_existente:
            comissoes_ja_existentes += 1
            print(f"  ⏭️  Venda #{venda.id} - Comissão já existe (R$ {comissao_existente.valor_comissao:,.2f})")
            continue
        
        # Calcular faturamento mensal do consultor
        consultor = venda.consultor
        data_venda = venda.data_venda or venda.data_criacao
        mes = data_venda.month
        ano = data_venda.year
        
        # Buscar todas as vendas do consultor no mesmo mês com entrada paga
        faturamento_mes = Venda.objects.filter(
            consultor=consultor,
            status_pagamento_entrada='PAGO',
            data_venda__year=ano,
            data_venda__month=mes
        ).aggregate(total=Sum('valor_entrada'))['total'] or Decimal('0')
        
        # Determinar percentual baseado no faturamento
        if faturamento_mes >= Decimal('80000'):
            percentual = Decimal('10.0')
        elif faturamento_mes >= Decimal('60000'):
            percentual = Decimal('6.0')
        elif faturamento_mes >= Decimal('50000'):
            percentual = Decimal('5.0')
        elif faturamento_mes >= Decimal('40000'):
            percentual = Decimal('4.0')
        elif faturamento_mes >= Decimal('30000'):
            percentual = Decimal('3.0')
        elif faturamento_mes >= Decimal('20000'):
            percentual = Decimal('2.0')
        else:
            percentual = Decimal('0.0')
        
        # Se percentual é 0, não gera comissão
        if percentual == Decimal('0.0'):
            print(f"  ⚠️  Venda #{venda.id} - Faturamento abaixo de R$ 20.000 (R$ {faturamento_mes:,.2f}) - Sem comissão")
            continue
        
        # Calcular valor da comissão sobre a ENTRADA
        valor_entrada = venda.valor_entrada
        valor_comissao = (valor_entrada * percentual) / Decimal('100')
        
        # Criar comissão
        comissao = Comissao.objects.create(
            venda=venda,
            usuario=consultor,
            tipo_comissao='CONSULTOR_ENTRADA',
            valor_comissao=valor_comissao,
            percentual_comissao=percentual,
            status='pendente',
            observacoes=f'Comissão sobre entrada de R$ {valor_entrada:,.2f} (Faturamento mensal: R$ {faturamento_mes:,.2f} = {percentual}%)'
        )
        
        comissoes_consultor_criadas += 1
        print(f"  ✅ Venda #{venda.id} - Comissão criada:")
        print(f"      Consultor: {consultor.get_full_name() or consultor.email}")
        print(f"      Valor Entrada: R$ {valor_entrada:,.2f}")
        print(f"      Faturamento Mês: R$ {faturamento_mes:,.2f}")
        print(f"      Percentual: {percentual}%")
        print(f"      Comissão: R$ {valor_comissao:,.2f}")
        
    except Exception as e:
        erros.append(f"Venda #{venda.id}: {str(e)}")
        print(f"  ❌ Erro na Venda #{venda.id}: {str(e)}")

# ==========================================
# 3. RESUMO
# ==========================================
print("\n\n" + "=" * 100)
print("📊 RESUMO DA CORREÇÃO:")
print("=" * 100)

print(f"\n✅ Inconsistências de status corrigidas: {inconsistencias_corrigidas}")
print(f"✅ Comissões de consultores criadas: {comissoes_consultor_criadas}")
print(f"⏭️  Comissões já existentes: {comissoes_ja_existentes}")

if erros:
    print(f"\n❌ Erros encontrados ({len(erros)}):")
    for erro in erros:
        print(f"  - {erro}")

# Verificar totais atualizados
print("\n📊 TOTAIS ATUALIZADOS:")
comissoes_captador = Comissao.objects.filter(tipo_comissao='CAPTADOR_ENTRADA')
comissoes_consultor = Comissao.objects.filter(tipo_comissao='CONSULTOR_ENTRADA')

print(f"\nComissões CAPTADOR_ENTRADA: {comissoes_captador.count()}")
if comissoes_captador.exists():
    total = comissoes_captador.aggregate(total=Sum('valor_comissao'))['total'] or Decimal('0')
    print(f"  Valor total: R$ {total:,.2f}")
    print(f"  Pagas: {comissoes_captador.filter(status='paga').count()}")
    print(f"  Pendentes: {comissoes_captador.filter(status='pendente').count()}")

print(f"\nComissões CONSULTOR_ENTRADA: {comissoes_consultor.count()}")
if comissoes_consultor.exists():
    total = comissoes_consultor.aggregate(total=Sum('valor_comissao'))['total'] or Decimal('0')
    print(f"  Valor total: R$ {total:,.2f}")
    print(f"  Pagas: {comissoes_consultor.filter(status='paga').count()}")
    print(f"  Pendentes: {comissoes_consultor.filter(status='pendente').count()}")

print("\n" + "=" * 100)
print("✅ CORREÇÃO CONCLUÍDA!")
print("=" * 100)
