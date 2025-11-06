#!/usr/bin/env python
"""Script para verificar status de um lead específico"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistemaMrBaruchProjeto.settings')
django.setup()

from marketing.models import Lead
from financeiro.models import PixLevantamento

# Buscar lead ID 60
try:
    lead = Lead.objects.get(id=60)
    print(f"\n{'='*60}")
    print(f"DADOS DO LEAD ID: {lead.id}")
    print(f"{'='*60}")
    print(f"Nome: {lead.nome_completo}")
    print(f"Status: {lead.status} ({lead.get_status_display()})")
    print(f"fez_levantamento: {lead.fez_levantamento}")
    print(f"Data cadastro: {lead.data_cadastro}")
    print(f"Captador: {lead.captador}")
    print(f"Atendente: {lead.atendente}")
    
    # Buscar PIX associado
    pix = lead.pix_levantamentos.order_by('-data_criacao').first()
    if pix:
        print(f"\n--- PIX LEVANTAMENTO ---")
        print(f"PIX ID: {pix.id}")
        print(f"Status Pagamento: {pix.status_pagamento}")
        print(f"Valor: R$ {pix.valor}")
        print(f"Data Criação: {pix.data_criacao}")
    else:
        print(f"\n--- SEM PIX LEVANTAMENTO ---")
    
    print(f"{'='*60}\n")
except Lead.DoesNotExist:
    print("\n❌ Lead ID 60 não encontrado!\n")
except Exception as e:
    print(f"\n❌ Erro: {e}\n")
