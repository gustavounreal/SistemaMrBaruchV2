"""
Script para adicionar a Entrada 1 faltante na Pré-Venda 17
"""
import os
import django
import sys
from decimal import Decimal
from datetime import date

# Configurar Django
sys.path.append(r'c:\Users\Root\Desktop\sistemaMrBaruch_Versão 2025\sistemaMrBaruch\sistemaMrBaruchProjeto')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistemaMrBaruchProjeto.settings')
django.setup()

from vendas.models import PreVenda, EntradaPreVenda

try:
    # Buscar pré-venda 17
    pre_venda = PreVenda.objects.get(id=17)
    
    print(f"\n{'='*60}")
    print(f"PRÉ-VENDA #{pre_venda.id}")
    print(f"{'='*60}")
    print(f"Cliente: {pre_venda.lead.nome_completo}")
    print(f"Valor Total: R$ {pre_venda.valor_total}")
    print(f"Valor Entrada (campo): R$ {pre_venda.valor_entrada}")
    
    # Verificar entradas existentes
    print(f"\n📊 ENTRADAS ATUAIS:")
    entradas_existentes = pre_venda.entradas.all()
    if entradas_existentes.exists():
        for entrada in entradas_existentes:
            print(f"   Entrada {entrada.numero_entrada}: R$ {entrada.valor} - {entrada.data_vencimento} - {entrada.forma_pagamento}")
    else:
        print("   Nenhuma entrada encontrada")
    
    # Verificar se já existe Entrada 1
    entrada_1_existe = pre_venda.entradas.filter(numero_entrada=1).exists()
    
    if entrada_1_existe:
        print(f"\n✅ Entrada 1 já existe, nada a fazer.")
    else:
        print(f"\n⚠️ Entrada 1 está faltando!")
        print(f"\n🔧 Adicionando Entrada 1...")
        
        # Criar Entrada 1 com R$ 350,00
        # Data: 1 semana antes da Entrada 2
        entrada_2 = pre_venda.entradas.filter(numero_entrada=2).first()
        if entrada_2:
            from datetime import timedelta
            data_entrada_1 = entrada_2.data_vencimento - timedelta(days=7)
        else:
            data_entrada_1 = date(2025, 11, 12)  # Data padrão
        
        EntradaPreVenda.objects.create(
            pre_venda=pre_venda,
            numero_entrada=1,
            valor=Decimal('350.00'),
            data_vencimento=data_entrada_1,
            forma_pagamento='PIX'
        )
        
        print(f"   ✅ Entrada 1 criada: R$ 350,00")
        print(f"      Data Vencimento: {data_entrada_1}")
        print(f"      Forma: PIX")
        
        # Atualizar valor_entrada (soma das entradas)
        total_entradas = pre_venda.entradas.aggregate(total=django.db.models.Sum('valor'))['total'] or Decimal('0')
        pre_venda.valor_entrada = total_entradas
        pre_venda.save()
        
        print(f"\n   💰 Valor total de entradas atualizado: R$ {total_entradas}")
    
    # Exibir resultado final
    print(f"\n{'='*60}")
    print(f"RESULTADO FINAL:")
    print(f"{'='*60}")
    entradas_finais = pre_venda.entradas.all().order_by('numero_entrada')
    for entrada in entradas_finais:
        print(f"   Entrada {entrada.numero_entrada}: R$ {entrada.valor} - {entrada.data_vencimento} - {entrada.forma_pagamento}")
    print(f"\n   💵 Total: R$ {pre_venda.valor_entrada}")
    print(f"\n{'='*60}\n")
    
except PreVenda.DoesNotExist:
    print(f"\n❌ Pré-venda #17 não encontrada!")
except Exception as e:
    print(f"\n❌ Erro: {e}")
    import traceback
    traceback.print_exc()
