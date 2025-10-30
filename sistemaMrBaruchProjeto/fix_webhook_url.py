#!/usr/bin/env python
"""
Script para corrigir URL do webhook do Asaas
Execute na VPS: python fix_webhook_url.py
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistemaMrBaruchProjeto.settings')
django.setup()

import requests
from core.asaas_webhook_manager import AsaasWebhookManager

def fix_webhook_url():
    webhook_id = '73d62c00-9c40-42e4-83c6-2479c05b8174'
    manager = AsaasWebhookManager()
    
    print("="*60)
    print("🔧 CORRIGINDO URL DO WEBHOOK ASAAS")
    print("="*60)
    
    # Verificar configuração atual
    result = manager.get_webhook_details(webhook_id)
    
    print("\n📋 WEBHOOK ATUAL:")
    print(f"  Status: {result.get('status')}")
    print(f"  URL: {result.get('webhook_url')}")
    print(f"  Enabled: {result.get('enabled')}")
    print(f"  Interrupted: {result.get('interrupted')}")
    
    # Descobrir qual URL usar
    print("\n" + "="*60)
    print("ESCOLHA A URL DO WEBHOOK:")
    print("="*60)
    print("1. http://155.138.193.148:8000/webhook/asaas/  (IP direto - desenvolvimento)")
    print("2. Digitar URL customizada (ex: https://mrbaruch.com.br/webhook/asaas/)")
    print("="*60)
    
    escolha = input("\nEscolha uma opção (1 ou 2): ").strip()
    
    if escolha == "1":
        nova_url = "http://155.138.193.148:8000/webhook/asaas/"
    elif escolha == "2":
        nova_url = input("Digite a URL completa: ").strip()
        if not nova_url:
            print("❌ URL não pode ser vazia!")
            return
    else:
        print("❌ Opção inválida!")
        return
    
    # Confirmar
    print(f"\n🔄 Atualizando webhook para: {nova_url}")
    confirmacao = input("Confirmar? (s/n): ").strip().lower()
    
    if confirmacao != 's':
        print("❌ Operação cancelada!")
        return
    
    # Atualizar webhook
    url = f"{manager.base_url}/webhooks/{webhook_id}"
    dados = {
        "url": nova_url,
        "enabled": True
    }
    
    try:
        response = requests.put(
            url,
            headers=manager.headers,
            json=dados,
            timeout=30
        )
        
        if response.status_code == 200:
            print("\n" + "="*60)
            print("✅ WEBHOOK ATUALIZADO COM SUCESSO!")
            print("="*60)
            print(f"Nova URL: {nova_url}")
            print("\n🔍 Verificando alteração...")
            
            # Verificar
            result = manager.get_webhook_details(webhook_id)
            print(f"URL atual: {result.get('webhook_url')}")
            print(f"Status: {result.get('status')}")
            print("="*60)
        else:
            print(f"\n❌ Erro ao atualizar: {response.status_code}")
            print(f"Resposta: {response.text}")
            
    except Exception as e:
        print(f"\n❌ Erro: {str(e)}")

if __name__ == "__main__":
    fix_webhook_url()
