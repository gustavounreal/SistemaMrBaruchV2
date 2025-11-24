#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SCRIPT DE SINCRONIZAÇÃO AUTOMÁTICA DO ASAAS
============================================
Sincroniza dados do Asaas com o banco local de forma automática:
- Atualiza dados que existem em ambos
- Adiciona dados novos do Asaas
- Remove dados locais que não existem mais no Asaas

Uso: python sincronizar_asaas_auto.py [principal|alternativo]
"""
import os
import sys
import io
import django
import time
import requests
from datetime import datetime
from decimal import Decimal

# Configurar encoding UTF-8
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistemaMrBaruchProjeto.settings')
django.setup()

from django.conf import settings
from django.utils import timezone
from asaas_sync.models import (
    AsaasClienteSyncronizado, AsaasCobrancaSyncronizada,
    AsaasClienteSyncronizado2, AsaasCobrancaSyncronizada2,
    AsaasSyncronizacaoLog
)


class SincronizadorAsaasAuto:
    """Sincronizador automático do Asaas"""
    
    def __init__(self, conta="principal"):
        self.conta = conta
        
        # Definir token e models baseado na conta
        if conta == "alternativo":
            self.api_token = getattr(settings, 'ASAAS_ALTERNATIVO_TOKEN', '')
            self.ModelCliente = AsaasClienteSyncronizado2
            self.ModelCobranca = AsaasCobrancaSyncronizada2
            self.tipo_sync = 'ALTERNATIVO'
        else:
            self.api_token = getattr(settings, 'ASAAS_API_TOKEN', '')
            self.ModelCliente = AsaasClienteSyncronizado
            self.ModelCobranca = AsaasCobrancaSyncronizada
            self.tipo_sync = 'COMPLETO'
        
        self.base_url = getattr(settings, 'ASAAS_API_URL', 'https://api.asaas.com/v3')
        self.headers = {
            'Content-Type': 'application/json',
            'access_token': self.api_token
        }
        self.timeout = 120
        
        # Estatísticas
        self.stats = {
            'clientes': {'total': 0, 'novos': 0, 'atualizados': 0, 'excluidos': 0},
            'cobrancas': {'total': 0, 'novas': 0, 'atualizadas': 0, 'excluidas': 0}
        }
        
        # Criar log
        self.log = AsaasSyncronizacaoLog.objects.create(
            tipo_sincronizacao=self.tipo_sync,
            status='EM_ANDAMENTO',
            usuario='Sistema Auto'
        )
    
    def fazer_requisicao(self, endpoint, params=None):
        """Faz requisição à API do Asaas com retry"""
        url = f"{self.base_url}/{endpoint}"
        
        for tentativa in range(1, 4):
            try:
                response = requests.get(url, headers=self.headers, params=params, timeout=self.timeout)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    print(f"[AVISO] Rate limit - aguardando {tentativa * 5}s...")
                    time.sleep(tentativa * 5)
                else:
                    print(f"[ERRO] Status {response.status_code}: {response.text[:200]}")
                    if tentativa < 3:
                        time.sleep(tentativa * 2)
                        
            except Exception as e:
                print(f"[ERRO] Tentativa {tentativa}/3: {str(e)}")
                if tentativa < 3:
                    time.sleep(tentativa * 2)
        
        return None
    
    def baixar_todos_clientes(self):
        """Baixa TODOS os clientes do Asaas"""
        print("\n" + "="*80)
        print(f"[CLIENTES] Baixando todos os clientes do Asaas {self.conta.upper()}")
        print("="*80)
        
        clientes_asaas = []
        offset = 0
        limit = 100
        
        while True:
            print(f"[PAGINA] Offset {offset}...")
            response = self.fazer_requisicao('customers', {'offset': offset, 'limit': limit})
            
            if not response:
                break
            
            clientes_pagina = response.get('data', [])
            if not clientes_pagina:
                break
            
            clientes_asaas.extend(clientes_pagina)
            print(f"[OK] {len(clientes_asaas)} clientes baixados...")
            
            if not response.get('hasMore', False):
                break
            
            offset += limit
            time.sleep(0.5)
        
        print(f"\n[OK] Total: {len(clientes_asaas)} clientes baixados do Asaas")
        return clientes_asaas
    
    def baixar_todas_cobrancas(self, clientes_ids):
        """Baixa TODAS as cobranças de todos os clientes"""
        print("\n" + "="*80)
        print(f"[COBRANCAS] Baixando todas as cobranças")
        print("="*80)
        
        cobrancas_asaas = []
        total_clientes = len(clientes_ids)
        
        for i, customer_id in enumerate(clientes_ids, 1):
            if i % 50 == 0:
                print(f"[PROGRESSO] {i}/{total_clientes} clientes processados...")
            
            offset = 0
            limit = 100
            
            while True:
                response = self.fazer_requisicao(f'payments', {
                    'customer': customer_id,
                    'offset': offset,
                    'limit': limit
                })
                
                if not response:
                    break
                
                cobrancas_pagina = response.get('data', [])
                if not cobrancas_pagina:
                    break
                
                # Adicionar customer_id em cada cobrança
                for cobranca in cobrancas_pagina:
                    cobranca['_customer_id'] = customer_id
                
                cobrancas_asaas.extend(cobrancas_pagina)
                
                if not response.get('hasMore', False):
                    break
                
                offset += limit
                time.sleep(0.3)
        
        print(f"\n[OK] Total: {len(cobrancas_asaas)} cobranças baixadas")
        return cobrancas_asaas
    
    def sincronizar_clientes(self, clientes_asaas):
        """Sincroniza clientes: atualiza, adiciona e exclui"""
        print("\n" + "="*80)
        print("[SYNC] Sincronizando clientes com o banco local")
        print("="*80)
        
        # IDs dos clientes no Asaas
        asaas_customer_ids = set(c['id'] for c in clientes_asaas if c.get('id'))
        
        # Processar cada cliente do Asaas
        for cliente_data in clientes_asaas:
            asaas_id = cliente_data.get('id')
            if not asaas_id:
                continue
            
            try:
                # Buscar ou criar cliente
                cliente, criado = self.ModelCliente.objects.update_or_create(
                    asaas_customer_id=asaas_id,
                    defaults={
                        'nome': cliente_data.get('name', ''),
                        'cpf_cnpj': cliente_data.get('cpfCnpj', ''),
                        'email': cliente_data.get('email', ''),
                        'telefone': cliente_data.get('phone', ''),
                        'celular': cliente_data.get('mobilePhone', ''),
                        'cep': cliente_data.get('postalCode', ''),
                        'endereco': cliente_data.get('address', ''),
                        'numero': cliente_data.get('addressNumber', ''),
                        'complemento': cliente_data.get('complement', ''),
                        'bairro': cliente_data.get('province', ''),
                        'cidade': cliente_data.get('city', ''),
                        'estado': cliente_data.get('state', ''),
                        'inscricao_municipal': cliente_data.get('municipalInscription', ''),
                        'inscricao_estadual': cliente_data.get('stateInscription', ''),
                        'observacoes': cliente_data.get('observations', ''),
                        'external_reference': cliente_data.get('externalReference', ''),
                        'notificacoes_desabilitadas': cliente_data.get('notificationDisabled', False),
                    }
                )
                
                if criado:
                    self.stats['clientes']['novos'] += 1
                else:
                    self.stats['clientes']['atualizados'] += 1
                
                self.stats['clientes']['total'] += 1
                
            except Exception as e:
                print(f"[ERRO] Erro ao sincronizar cliente {asaas_id}: {str(e)}")
        
        # Excluir clientes locais que não existem mais no Asaas
        clientes_para_excluir = self.ModelCliente.objects.exclude(asaas_customer_id__in=asaas_customer_ids)
        qtd_excluir = clientes_para_excluir.count()
        
        if qtd_excluir > 0:
            print(f"\n[LIMPEZA] Excluindo {qtd_excluir} clientes que não existem mais no Asaas...")
            clientes_para_excluir.delete()
            self.stats['clientes']['excluidos'] = qtd_excluir
        
        print(f"\n[OK] Clientes sincronizados:")
        print(f"   Total: {self.stats['clientes']['total']}")
        print(f"   Novos: {self.stats['clientes']['novos']}")
        print(f"   Atualizados: {self.stats['clientes']['atualizados']}")
        print(f"   Excluídos: {self.stats['clientes']['excluidos']}")
    
    def sincronizar_cobrancas(self, cobrancas_asaas):
        """Sincroniza cobranças: atualiza, adiciona e exclui"""
        print("\n" + "="*80)
        print("[SYNC] Sincronizando cobranças com o banco local")
        print("="*80)
        
        # IDs das cobranças no Asaas
        asaas_payment_ids = set(c['id'] for c in cobrancas_asaas if c.get('id'))
        
        # Processar cada cobrança do Asaas
        for cobranca_data in cobrancas_asaas:
            asaas_id = cobranca_data.get('id')
            customer_id = cobranca_data.get('_customer_id') or cobranca_data.get('customer')
            
            if not asaas_id or not customer_id:
                continue
            
            try:
                # Buscar cliente
                try:
                    cliente = self.ModelCliente.objects.get(asaas_customer_id=customer_id)
                except self.ModelCliente.DoesNotExist:
                    print(f"[AVISO] Cliente {customer_id} não encontrado para cobrança {asaas_id}")
                    continue
                
                # Determinar tipo de cobrança
                billing_type = cobranca_data.get('billingType', 'UNDEFINED')
                tipo_cobranca = billing_type if billing_type in ['BOLETO', 'CREDIT_CARD', 'PIX'] else 'UNDEFINED'
                
                # Buscar ou criar cobrança
                cobranca, criada = self.ModelCobranca.objects.update_or_create(
                    asaas_payment_id=asaas_id,
                    defaults={
                        'cliente': cliente,
                        'tipo_cobranca': tipo_cobranca,
                        'status': cobranca_data.get('status', 'PENDING'),
                        'valor': Decimal(str(cobranca_data.get('value', 0))),
                        'valor_liquido': Decimal(str(cobranca_data.get('netValue', 0))) if cobranca_data.get('netValue') else None,
                        'descricao': cobranca_data.get('description', ''),
                        'data_vencimento': self._parse_date(cobranca_data.get('dueDate')),
                        'data_pagamento': self._parse_date(cobranca_data.get('paymentDate')),
                        'invoice_url': cobranca_data.get('invoiceUrl', ''),
                        'bank_slip_url': cobranca_data.get('bankSlipUrl', ''),
                        'pix_qrcode_url': cobranca_data.get('pixQrCodeUrl', ''),
                        'pix_copy_paste': cobranca_data.get('pixCopyPaste', ''),
                        'external_reference': cobranca_data.get('externalReference', ''),
                    }
                )
                
                if criada:
                    self.stats['cobrancas']['novas'] += 1
                else:
                    self.stats['cobrancas']['atualizadas'] += 1
                
                self.stats['cobrancas']['total'] += 1
                
            except Exception as e:
                print(f"[ERRO] Erro ao sincronizar cobrança {asaas_id}: {str(e)}")
        
        # Excluir cobranças locais que não existem mais no Asaas
        cobrancas_para_excluir = self.ModelCobranca.objects.exclude(asaas_payment_id__in=asaas_payment_ids)
        qtd_excluir = cobrancas_para_excluir.count()
        
        if qtd_excluir > 0:
            print(f"\n[LIMPEZA] Excluindo {qtd_excluir} cobranças que não existem mais no Asaas...")
            cobrancas_para_excluir.delete()
            self.stats['cobrancas']['excluidas'] = qtd_excluir
        
        print(f"\n[OK] Cobranças sincronizadas:")
        print(f"   Total: {self.stats['cobrancas']['total']}")
        print(f"   Novas: {self.stats['cobrancas']['novas']}")
        print(f"   Atualizadas: {self.stats['cobrancas']['atualizadas']}")
        print(f"   Excluídas: {self.stats['cobrancas']['excluidas']}")
    
    def _parse_date(self, date_string):
        """Converte string para date"""
        if not date_string:
            return None
        try:
            return datetime.strptime(date_string, '%Y-%m-%d').date()
        except:
            return None
    
    def executar(self):
        """Executa sincronização completa"""
        print("\n" + "="*80)
        print(f"SINCRONIZAÇÃO AUTOMÁTICA - ASAAS {self.conta.upper()}")
        print("="*80)
        
        inicio = time.time()
        
        try:
            # 1. Baixar todos os clientes do Asaas
            clientes_asaas = self.baixar_todos_clientes()
            
            if not clientes_asaas:
                raise Exception("Nenhum cliente foi baixado do Asaas")
            
            # 2. Baixar todas as cobranças
            clientes_ids = [c['id'] for c in clientes_asaas if c.get('id')]
            cobrancas_asaas = self.baixar_todas_cobrancas(clientes_ids)
            
            # 3. Sincronizar clientes (atualizar, adicionar, excluir)
            self.sincronizar_clientes(clientes_asaas)
            
            # 4. Sincronizar cobranças (atualizar, adicionar, excluir)
            self.sincronizar_cobrancas(cobrancas_asaas)
            
            # Finalizar log
            duracao = time.time() - inicio
            self.log.status = 'SUCESSO'
            self.log.data_fim = timezone.now()
            self.log.total_clientes = self.stats['clientes']['total']
            self.log.clientes_novos = self.stats['clientes']['novos']
            self.log.clientes_atualizados = self.stats['clientes']['atualizados']
            self.log.total_cobrancas = self.stats['cobrancas']['total']
            self.log.cobrancas_novas = self.stats['cobrancas']['novas']
            self.log.cobrancas_atualizadas = self.stats['cobrancas']['atualizadas']
            self.log.duracao_segundos = int(duracao)
            self.log.mensagem = f"""Sincronização automática concluída - {self.conta}

CLIENTES:
  Total: {self.stats['clientes']['total']}
  Novos: {self.stats['clientes']['novos']}
  Atualizados: {self.stats['clientes']['atualizados']}
  Excluídos: {self.stats['clientes']['excluidos']}

COBRANÇAS:
  Total: {self.stats['cobrancas']['total']}
  Novas: {self.stats['cobrancas']['novas']}
  Atualizadas: {self.stats['cobrancas']['atualizadas']}
  Excluídas: {self.stats['cobrancas']['excluidas']}

Duração: {duracao:.0f}s"""
            self.log.save()
            
            print("\n" + "="*80)
            print("SINCRONIZAÇÃO CONCLUÍDA COM SUCESSO!")
            print(f"Tempo: {duracao:.0f}s ({duracao/60:.1f}min)")
            print("="*80)
            
            return True
            
        except Exception as e:
            # Registrar erro
            duracao = time.time() - inicio
            self.log.status = 'ERRO'
            self.log.data_fim = timezone.now()
            self.log.duracao_segundos = int(duracao)
            self.log.erros = str(e)
            self.log.save()
            
            print(f"\n[ERRO] Erro na sincronização: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return False


if __name__ == '__main__':
    # Verificar argumentos
    if len(sys.argv) > 1:
        args = [arg for arg in sys.argv[1:] if not arg.startswith('--')]
        if args:
            conta = args[0].lower()
            if conta not in ['principal', 'alternativo']:
                print("[ERRO] Conta inválida! Use: principal ou alternativo")
                sys.exit(1)
        else:
            conta = 'principal'
    else:
        conta = 'principal'
    
    print(f"\n[INFO] Conta selecionada: {conta.upper()}")
    print("[INFO] Sincronização automática - sem confirmação necessária")
    
    # Executar
    sincronizador = SincronizadorAsaasAuto(conta=conta)
    
    try:
        sucesso = sincronizador.executar()
        sys.exit(0 if sucesso else 1)
    except KeyboardInterrupt:
        print("\n\n[ERRO] Interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERRO] ERRO: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
