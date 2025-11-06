#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para verificar detalhadamente cada PIX e sua comissão
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistemaMrBaruchProjeto.settings')
django.setup()

from financeiro.models import PixLevantamento
from comissoes.models import ComissaoLead

print("=" * 120)
print("🔍 VERIFICAÇÃO DETALHADA: PIX x COMISSÕES")
print("=" * 120)

pix_pagos = PixLevantamento.objects.filter(status_pagamento='pago').order_by('id')

print(f"\nTotal de PIX pagos: {pix_pagos.count()}\n")

pix_sem_comissao = []
pix_com_comissao = []

for pix in pix_pagos:
    lead = pix.lead
    comissao = ComissaoLead.objects.filter(lead=lead).first()
    
    print(f"PIX #{pix.id:3d} | Lead #{lead.id:3d} | {lead.nome_completo:30s}", end=" | ")
    
    if lead.atendente:
        print(f"Atendente: {lead.atendente.get_full_name() or lead.atendente.email:30s}", end=" | ")
    else:
        print(f"{'SEM ATENDENTE':30s}", end=" | ")
    
    if comissao:
        print(f"✅ Comissão #{comissao.id:3d} - {comissao.status:12s} - R$ {comissao.valor:.2f}")
        pix_com_comissao.append(pix)
    else:
        print(f"❌ SEM COMISSÃO")
        pix_sem_comissao.append(pix)

print("\n" + "=" * 120)
print("📊 RESUMO:")
print("=" * 120)
print(f"\n✅ PIX com comissão: {len(pix_com_comissao)}")
print(f"❌ PIX sem comissão: {len(pix_sem_comissao)}")

if pix_sem_comissao:
    print(f"\n⚠️  ATENÇÃO: {len(pix_sem_comissao)} PIX(s) sem comissão!")
    print("\nDetalhes:")
    for pix in pix_sem_comissao:
        lead = pix.lead
        print(f"\n  PIX #{pix.id}:")
        print(f"    Lead: #{lead.id} - {lead.nome_completo}")
        print(f"    Data: {pix.data_criacao.strftime('%d/%m/%Y %H:%M')}")
        print(f"    Valor: R$ {pix.valor:.2f}")
        if lead.atendente:
            print(f"    Atendente: {lead.atendente.get_full_name() or lead.atendente.email}")
        else:
            print(f"    ⚠️  SEM ATENDENTE VINCULADO")

print("\n" + "=" * 120)
