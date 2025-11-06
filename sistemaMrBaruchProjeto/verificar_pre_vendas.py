#!/usr/bin/env python
"""Script para verificar valores de pré-vendas"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistemaMrBaruchProjeto.settings')
django.setup()

from vendas.models import PreVenda
from decimal import Decimal

print("\n" + "="*70)
print("VERIFICAÇÃO DE VALORES DE PRÉ-VENDAS")
print("="*70)

# Buscar todas as pré-vendas
pre_vendas = PreVenda.objects.all().order_by('-data_criacao')[:5]

if not pre_vendas:
    print("\n❌ Nenhuma pré-venda encontrada!")
else:
    for pv in pre_vendas:
        print(f"\n{'─'*70}")
        print(f"ID: {pv.id} | Lead: {pv.lead.nome_completo}")
        print(f"Status: {pv.status}")
        print(f"Serviço: {pv.get_servico_interesse_display()}")
        print(f"\n💰 VALORES:")
        print(f"  Valor Proposto: R$ {pv.valor_proposto}")
        print(f"  Valor Total: R$ {pv.valor_total}")
        print(f"  Valor Entrada: R$ {pv.valor_entrada}")
        print(f"  Quantidade Parcelas: {pv.quantidade_parcelas}")
        print(f"  Valor Parcela: R$ {pv.valor_parcela}")
        print(f"  Frequência: {pv.frequencia_pagamento}")
        
        # Validação
        if pv.valor_total and pv.valor_total < Decimal('100'):
            print(f"\n  ⚠️ ATENÇÃO: Valor total parece incorreto (muito baixo): R$ {pv.valor_total}")
        if pv.valor_parcela and pv.valor_parcela < Decimal('10'):
            print(f"  ⚠️ ATENÇÃO: Valor parcela parece incorreto (muito baixo): R$ {pv.valor_parcela}")

print("\n" + "="*70 + "\n")
