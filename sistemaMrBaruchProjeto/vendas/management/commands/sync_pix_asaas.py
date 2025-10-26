"""
Comando para sincronizar PIX de entrada do ASAAS que não foram salvos no banco
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from vendas.models import Venda
from financeiro.models import PixEntrada, ClienteAsaas
from core.asaas_service import AsaasService


class Command(BaseCommand):
    help = 'Sincroniza PIX de entrada do ASAAS que não foram salvos no banco de dados'

    def add_arguments(self, parser):
        parser.add_argument(
            '--venda-id',
            type=int,
            help='ID específico da venda para sincronizar PIX'
        )

    def handle(self, *args, **options):
        venda_id = options.get('venda_id')
        
        if venda_id:
            vendas = Venda.objects.filter(id=venda_id)
        else:
            # Busca vendas com entrada > 0 mas sem PIX cadastrado
            vendas = Venda.objects.filter(valor_entrada__gt=0).exclude(
                pix_entradas__isnull=False
            )
        
        self.stdout.write(f"🔍 Verificando {vendas.count()} venda(s)...")
        
        asaas = AsaasService()
        total_sincronizados = 0
        
        for venda in vendas:
            self.stdout.write(f"\n📋 Venda #{venda.id} - {venda.cliente.lead.nome_completo}")
            self.stdout.write(f"   Valor da Entrada: R$ {venda.valor_entrada}")
            
            # Verifica se já tem PIX cadastrado
            pix_existente = PixEntrada.objects.filter(venda=venda).first()
            if pix_existente:
                self.stdout.write(self.style.WARNING(f"   ⏭️ PIX já existe: {pix_existente.asaas_payment_id}"))
                continue
            
            # Busca cliente ASAAS
            try:
                cliente_asaas = ClienteAsaas.objects.get(lead=venda.cliente.lead)
                if not cliente_asaas.asaas_customer_id:
                    self.stdout.write(self.style.ERROR("   ❌ Cliente ASAAS sem customer_id"))
                    continue
                
                self.stdout.write(f"   ✅ Cliente ASAAS: {cliente_asaas.asaas_customer_id}")
                
                # Busca cobranças do cliente no ASAAS
                # Endpoint: GET /v3/payments?customer={customer_id}
                params = {
                    'customer': cliente_asaas.asaas_customer_id,
                    'billingType': 'PIX'
                }
                
                response = asaas._fazer_requisicao('GET', 'payments', params=params)
                
                if response and 'data' in response:
                    cobrancas = response['data']
                    self.stdout.write(f"   📊 {len(cobrancas)} cobrança(s) PIX encontrada(s)")
                    
                    # Filtra cobranças com external_reference da venda
                    for cobranca in cobrancas:
                        external_ref = cobranca.get('externalReference', '')
                        if f'venda_{venda.id}_entrada' in external_ref:
                            self.stdout.write(f"   🎯 Cobrança encontrada: {cobranca['id']}")
                            
                            # Busca QR Code
                            qr_data = asaas.obter_qr_code_pix(cobranca['id'])
                            
                            pix_code = qr_data.get('payload', '') if qr_data else ''
                            pix_qr_url = qr_data.get('encodedImage', '') if qr_data else ''
                            
                            if not pix_code:
                                pix_code = cobranca.get('invoiceUrl', f'PIX ID: {cobranca["id"]}')
                            
                            # Cria PIX no banco
                            with transaction.atomic():
                                pix_entrada = PixEntrada.objects.create(
                                    venda=venda,
                                    asaas_payment_id=cobranca['id'],
                                    valor=venda.valor_entrada,
                                    pix_code=pix_code,
                                    pix_qr_code_url=pix_qr_url,
                                    status_pagamento='pendente'
                                )
                                
                                self.stdout.write(self.style.SUCCESS(
                                    f"   ✅ PIX salvo no banco: ID={pix_entrada.id}"
                                ))
                                total_sincronizados += 1
                            break
                    else:
                        self.stdout.write(self.style.WARNING(
                            "   ⚠️ Nenhuma cobrança com external_reference correspondente"
                        ))
                else:
                    self.stdout.write(self.style.ERROR("   ❌ Erro ao buscar cobranças no ASAAS"))
                    
            except ClienteAsaas.DoesNotExist:
                self.stdout.write(self.style.ERROR("   ❌ Cliente ASAAS não encontrado"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   ❌ Erro: {str(e)}"))
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS(
            f"✅ Sincronização concluída! {total_sincronizados} PIX(s) sincronizado(s)."
        ))
