import sqlite3
import sys

# Conectar ao banco de dados
db_path = r"c:\Users\Root\Desktop\sistemaMrBaruch_Versão 2025\sistemaMrBaruch\sistemaMrBaruchProjeto\db.sqlite3"

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # ID da pré-venda para consultar
    pre_venda_id = 17
    
    print(f"\n{'='*60}")
    print(f"DIAGNÓSTICO - PRÉ-VENDA ID: {pre_venda_id}")
    print(f"{'='*60}\n")
    
    # Consultar dados da pré-venda
    cursor.execute("""
        SELECT id, valor_total, valor_entrada, status
        FROM vendas_prevenda
        WHERE id = ?
    """, (pre_venda_id,))
    
    pre_venda = cursor.fetchone()
    if pre_venda:
        print(f"📋 PRÉ-VENDA:")
        print(f"   ID: {pre_venda[0]}")
        print(f"   Valor Total: R$ {pre_venda[1]:.2f}")
        print(f"   Valor Entrada (campo antigo): R$ {pre_venda[2]:.2f if pre_venda[2] else 0:.2f}")
        print(f"   Status: {pre_venda[3]}")
    else:
        print(f"❌ Pré-venda ID {pre_venda_id} não encontrada!")
        sys.exit(1)
    
    # Consultar entradas da pré-venda
    print(f"\n💰 ENTRADAS CADASTRADAS:")
    cursor.execute("""
        SELECT id, numero_entrada, valor, data_vencimento, forma_pagamento
        FROM vendas_entradaprevenda
        WHERE pre_venda_id = ?
        ORDER BY numero_entrada
    """, (pre_venda_id,))
    
    entradas = cursor.fetchall()
    if entradas:
        print(f"   Total de entradas: {len(entradas)}")
        total_entradas = 0
        for entrada in entradas:
            print(f"\n   Entrada {entrada[1]}:")
            print(f"      ID: {entrada[0]}")
            print(f"      Valor: R$ {entrada[2]:.2f}")
            print(f"      Vencimento: {entrada[3]}")
            print(f"      Forma Pagamento: {entrada[4]}")
            total_entradas += entrada[2]
        
        print(f"\n   💵 Total das entradas: R$ {total_entradas:.2f}")
    else:
        print("   ⚠️ Nenhuma entrada encontrada na tabela vendas_entradaprevenda!")
    
    print(f"\n{'='*60}\n")
    
    conn.close()
    
except sqlite3.Error as e:
    print(f"❌ Erro ao acessar banco de dados: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Erro inesperado: {e}")
    sys.exit(1)
