#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistemaMrBaruchProjeto.settings')
django.setup()

from financeiro.models import Comissao
from comissoes.models import ComissaoCaptador

print("=== VERIFICANDO MODELOS DE COMISSÃO ===\n")

print("1. Comissões no modelo financeiro.Comissao:")
comissoes_financeiro = Comissao.objects.filter(tipo_comissao__in=['CAPTADOR_ENTRADA', 'CAPTADOR_PARCELA'])
print(f"   Total: {comissoes_financeiro.count()}")
for c in comissoes_financeiro[:5]:
    print(f"   - #{c.id}: {c.tipo_comissao} - R$ {c.valor_comissao} - {c.status}")

print("\n2. Comissões no modelo comissoes.ComissaoCaptador:")
comissoes_captador = ComissaoCaptador.objects.all()
print(f"   Total: {comissoes_captador.count()}")
for c in comissoes_captador[:5]:
    print(f"   - #{c.id}: R$ {c.valor} - {c.status}")

print("\n=== CONCLUSÃO ===")
print(f"O painel está buscando em: comissoes.ComissaoCaptador ({comissoes_captador.count()} registros)")
print(f"As comissões estão em: financeiro.Comissao ({comissoes_financeiro.count()} registros)")
