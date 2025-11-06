#!/usr/bin/env python
"""Script para verificar os valores das vendas"""
import os
import sys
import django

# Adiciona o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistemaMrBaruchProjeto.settings')
django.setup()

from vendas.models import Venda

print("=" * 70)
print("DIAGNÓSTICO DE VALORES DAS VENDAS")
print("=" * 70)

vendas = Venda.objects.all().select_related('cliente', 'cliente__lead', 'servico')[:10]

print(f"\nTotal de vendas no banco: {Venda.objects.count()}")
print("\n" + "-" * 70)
print(f"{'ID':<5} {'Cliente':<25} {'Valor Total':<15} {'Entrada':<15}")
print("-" * 70)

for venda in vendas:
    cliente_nome = venda.cliente.lead.nome_completo if venda.cliente.lead else "Sem nome"
    print(f"#{venda.id:<4} {cliente_nome[:23]:<25} R$ {venda.valor_total:>10} R$ {venda.valor_entrada:>10}")

print("-" * 70)
print("\n✅ Diagnóstico concluído!")
