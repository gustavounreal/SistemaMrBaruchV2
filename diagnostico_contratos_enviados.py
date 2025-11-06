#!/usr/bin/env python
"""
Script de diagnóstico para contratos enviados
"""
import os
import sys
import django

# Setup Django
projeto_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sistemaMrBaruchProjeto')
sys.path.append(projeto_dir)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistemaMrBaruchProjeto.settings')
django.setup()

from juridico.models import Contrato
from django.db.models import Count

print("="*80)
print("DIAGNÓSTICO: CONTRATOS ENVIADOS")
print("="*80)

# Contar contratos por status
print("\n1. CONTAGEM POR STATUS:")
print("-" * 80)
status_count = Contrato.objects.values('status').annotate(total=Count('id')).order_by('-total')
for item in status_count:
    print(f"   {item['status']}: {item['total']} contrato(s)")

print("\n2. TOTAL DE CONTRATOS:")
print("-" * 80)
total = Contrato.objects.count()
print(f"   Total geral: {total} contratos")

print("\n3. CONTRATOS COM STATUS 'ENVIADO':")
print("-" * 80)
contratos_enviados = Contrato.objects.filter(status='ENVIADO').select_related(
    'venda', 'cliente', 'cliente__lead'
)
print(f"   Total enviados: {contratos_enviados.count()}")

if contratos_enviados.exists():
    print("\n   Detalhes dos contratos ENVIADOS:")
    for contrato in contratos_enviados:
        print(f"   - ID: {contrato.id}")
        print(f"     Número: {contrato.numero_contrato}")
        print(f"     Cliente: {contrato.cliente.lead.nome_completo}")
        print(f"     Status: {contrato.status}")
        print(f"     Data Envio: {contrato.data_envio}")
        print(f"     Dias com cliente: {contrato.dias_com_cliente}")
        print()
else:
    print("   ⚠️ Nenhum contrato com status ENVIADO encontrado!")

print("\n4. VERIFICAÇÃO DE RELACIONAMENTOS:")
print("-" * 80)
contratos_sem_venda = Contrato.objects.filter(venda__isnull=True).count()
contratos_sem_cliente = Contrato.objects.filter(cliente__isnull=True).count()
print(f"   Contratos sem venda: {contratos_sem_venda}")
print(f"   Contratos sem cliente: {contratos_sem_cliente}")

print("\n5. ÚLTIMOS 10 CONTRATOS (QUALQUER STATUS):")
print("-" * 80)
ultimos = Contrato.objects.select_related('cliente', 'cliente__lead').order_by('-data_criacao')[:10]
for contrato in ultimos:
    print(f"   - ID: {contrato.id} | Status: {contrato.status} | Cliente: {contrato.cliente.lead.nome_completo}")

print("\n" + "="*80)
