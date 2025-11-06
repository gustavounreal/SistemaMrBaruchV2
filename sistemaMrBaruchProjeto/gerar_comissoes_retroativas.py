"""
Script para gerar comissões retroativas de vendas já pagas
Execute: python manage.py shell < gerar_comissoes_retroativas.py
"""

from django.db.models import Q
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para gerar comissões retroativas de consultores e captadores
"""
import os
import sys
import django

# Configurar o Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistemaMrBaruchProjeto.settings')
django.setup()

from vendas.models import Venda, Parcela
from comissoes.services import gerar_comissao_venda_consultor, gerar_comissao_venda_captador
from decimal import Decimal

print("=" * 80)
print("GERANDO COMISSÕES RETROATIVAS")
print("=" * 80)

# 1. GERAR COMISSÕES DE CONSULTORES
print("\n📊 Gerando comissões de consultores...")
vendas_pagas = Venda.objects.filter(
    Q(status__in=['PAGO', 'ATIVO', 'CONCLUIDO']) |
    Q(parcelas__status='PAGO')
).distinct()

comissoes_consultor_criadas = 0
for venda in vendas_pagas:
    # Verificar se tem parcelas pagas
    parcelas_pagas = venda.parcelas.filter(status='PAGO')
    
    if parcelas_pagas.exists():
        # Gerar comissão por cada parcela paga
        for parcela in parcelas_pagas:
            try:
                comissao = gerar_comissao_venda_consultor(venda, parcela)
                if comissao:
                    comissoes_consultor_criadas += 1
                    print(f"  ✓ Comissão criada: Venda #{venda.id} - Parcela {parcela.numero_parcela} - R$ {comissao.valor}")
            except Exception as e:
                print(f"  ✗ Erro ao criar comissão para Venda #{venda.id} - Parcela {parcela.numero_parcela}: {e}")
    else:
        # Se não tem parcelas, verificar se a venda está paga
        if venda.status in ['PAGO', 'CONCLUIDO']:
            try:
                comissao = gerar_comissao_venda_consultor(venda)
                if comissao:
                    comissoes_consultor_criadas += 1
                    print(f"  ✓ Comissão criada: Venda #{venda.id} - R$ {comissao.valor}")
            except Exception as e:
                print(f"  ✗ Erro ao criar comissão para Venda #{venda.id}: {e}")

print(f"\n✅ Total de comissões de consultores criadas: {comissoes_consultor_criadas}")

# 2. GERAR COMISSÕES DE CAPTADORES
print("\n📊 Gerando comissões de captadores...")
vendas_com_captador = Venda.objects.filter(
    captador__isnull=False
).filter(
    Q(status__in=['PAGO', 'ATIVO', 'CONCLUIDO']) |
    Q(parcelas__status='PAGO')
).distinct()

comissoes_captador_criadas = 0
for venda in vendas_com_captador:
    # Verificar se tem parcelas pagas
    parcelas_pagas = venda.parcelas.filter(status='PAGO')
    
    if parcelas_pagas.exists():
        # Gerar comissão por cada parcela paga
        for parcela in parcelas_pagas:
            try:
                comissao = gerar_comissao_venda_captador(venda, parcela)
                if comissao:
                    comissoes_captador_criadas += 1
                    print(f"  ✓ Comissão criada: Venda #{venda.id} - Parcela {parcela.numero_parcela} - R$ {comissao.valor}")
            except Exception as e:
                print(f"  ✗ Erro ao criar comissão para Venda #{venda.id} - Parcela {parcela.numero_parcela}: {e}")
    else:
        # Se não tem parcelas, verificar se a venda está paga
        if venda.status in ['PAGO', 'CONCLUIDO']:
            try:
                comissao = gerar_comissao_venda_captador(venda)
                if comissao:
                    comissoes_captador_criadas += 1
                    print(f"  ✓ Comissão criada: Venda #{venda.id} - R$ {comissao.valor}")
            except Exception as e:
                print(f"  ✗ Erro ao criar comissão para Venda #{venda.id}: {e}")

print(f"\n✅ Total de comissões de captadores criadas: {comissoes_captador_criadas}")

# 3. RESUMO FINAL
print("\n" + "=" * 80)
print("RESUMO FINAL")
print("=" * 80)
print(f"Comissões de Consultores: {comissoes_consultor_criadas}")
print(f"Comissões de Captadores: {comissoes_captador_criadas}")
print(f"TOTAL: {comissoes_consultor_criadas + comissoes_captador_criadas}")
print("=" * 80)
