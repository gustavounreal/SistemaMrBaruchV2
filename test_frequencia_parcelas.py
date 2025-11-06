#!/usr/bin/env python
"""
Script de teste para verificar a geração de parcelas com diferentes frequências
"""
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

def testar_geracao_parcelas():
    """Testa a geração de parcelas para diferentes frequências"""
    
    frequencias = ['MENSAL', 'QUINZENAL', 'SEMANAL']
    quantidade_parcelas = 6
    valor_parcela = 100.00
    
    print("="*80)
    print("TESTE DE GERAÇÃO DE PARCELAS - PRÉ-VENDA")
    print("="*80)
    print(f"\nQuantidade de parcelas: {quantidade_parcelas}")
    print(f"Valor da parcela: R$ {valor_parcela:.2f}")
    print(f"Data base: {date.today().strftime('%d/%m/%Y')}\n")
    
    for frequencia in frequencias:
        print(f"\n{'='*80}")
        print(f"FREQUÊNCIA: {frequencia}")
        print(f"{'='*80}\n")
        
        parcelas = []
        data_venc = date.today() + timedelta(days=30)
        
        for i in range(1, quantidade_parcelas + 1):
            parcelas.append({
                'numero': i,
                'valor': valor_parcela,
                'vencimento': data_venc,
            })
            
            # Avança a data conforme periodicidade
            if frequencia == 'MENSAL':
                data_venc = data_venc + relativedelta(months=1)
            elif frequencia == 'QUINZENAL':
                data_venc = data_venc + timedelta(days=15)
            elif frequencia == 'SEMANAL':
                data_venc = data_venc + timedelta(days=7)
        
        # Exibir parcelas
        for parcela in parcelas:
            print(f"Parcela {parcela['numero']:2d}/{quantidade_parcelas} - "
                  f"R$ {parcela['valor']:7.2f} - "
                  f"Vencimento: {parcela['vencimento'].strftime('%d/%m/%Y')}")
        
        # Estatísticas
        primeira_parcela = parcelas[0]['vencimento']
        ultima_parcela = parcelas[-1]['vencimento']
        duracao_total = (ultima_parcela - primeira_parcela).days
        
        print(f"\nPrimeiro vencimento: {primeira_parcela.strftime('%d/%m/%Y')}")
        print(f"Último vencimento: {ultima_parcela.strftime('%d/%m/%Y')}")
        print(f"Duração total: {duracao_total} dias")
        print(f"Valor total: R$ {sum(p['valor'] for p in parcelas):.2f}")

if __name__ == '__main__':
    testar_geracao_parcelas()
