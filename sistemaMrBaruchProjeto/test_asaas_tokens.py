"""
Script para testar tokens ASAAS
"""
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistemaMrBaruchProjeto.settings')
django.setup()

import requests
from django.conf import settings

def testar_token(token, nome):
    """Testa um token ASAAS fazendo uma requisição simples"""
    print(f"\n{'='*60}")
    print(f"Testando {nome}")
    print(f"Token: {token[:20]}...")
    print(f"{'='*60}")
    
    url = "https://api.asaas.com/v3/customers"
    headers = {
        'Content-Type': 'application/json',
        'access_token': token
    }
    params = {'limit': 1, 'offset': 0}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            total = data.get('totalCount', 0)
            print(f"✅ TOKEN VÁLIDO!")
            print(f"Total de clientes: {total}")
            if data.get('data'):
                primeiro = data['data'][0]
                print(f"Primeiro cliente: {primeiro.get('name', 'N/A')}")
        elif response.status_code == 401:
            print(f"❌ TOKEN INVÁLIDO OU EXPIRADO")
            print(f"Resposta: {response.text[:200]}")
        else:
            print(f"⚠️ Erro {response.status_code}")
            print(f"Resposta: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ ERRO NA REQUISIÇÃO: {str(e)}")

if __name__ == '__main__':
    print("\n🔍 TESTANDO TOKENS ASAAS\n")
    
    # Token Principal
    token_principal = settings.ASAAS_API_TOKEN
    if token_principal:
        testar_token(token_principal, "TOKEN PRINCIPAL")
    else:
        print("❌ Token principal não configurado")
    
    # Token Alternativo
    token_alternativo = settings.ASAAS_ALTERNATIVO_TOKEN
    if token_alternativo:
        testar_token(token_alternativo, "TOKEN ALTERNATIVO")
    else:
        print("❌ Token alternativo não configurado")
    
    print("\n" + "="*60)
    print("TESTE CONCLUÍDO")
    print("="*60 + "\n")
