#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para remover emojis dos arquivos Python
"""
import sys
import io

# Forçar UTF-8 no Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def remover_emojis_arquivo(arquivo):
    """Remove emojis de um arquivo"""
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Mapeamento de emojis para texto
        replacements = {
            '📡': '[REQ]',
            '⚠️': '[AVISO]',
            '⚠': '[AVISO]',
            '❌': '[ERRO]',
            '🔽': '[DOWNLOAD]',
            '📄': '[PAGINA]',
            '✅': '[OK]',
            '📊': '[STATS]',
            '🔍': '[VALIDACAO]',
            '💾': '[SALVANDO]',
            '🎉': '[SUCESSO]',
            '⏱️': '[TEMPO]',
            '⏱': '[TEMPO]',
            '📝': '[PROXIMO]',
            '🚀': '[INICIO]',
            '💰': '[VALOR]',
            '👤': '[CLIENTE]',
            '🎯': '[CONTA]',
            '🗑️': '[DELETAR]',
            '🗑': '[DELETAR]',
            '🧹': '[LIMPEZA]',
            '📂': '[ARQUIVO]',
            '📁': '[PASTA]',
            '📋': '[LISTA]',
            '📥': '[IMPORTAR]',
            '🔄': '[SYNC]',
        }
        
        # Aplicar substituições
        original_len = len(content)
        for emoji, text in replacements.items():
            content = content.replace(emoji, text)
        
        # Salvar apenas se houver mudanças
        if len(content) != original_len or any(emoji in content for emoji in replacements.keys()):
            with open(arquivo, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f'[OK] Emojis removidos de {arquivo}')
            return True
        else:
            print(f'[INFO] Nenhum emoji encontrado em {arquivo}')
            return False
            
    except Exception as e:
        print(f'[ERRO] Erro ao processar {arquivo}: {str(e)}')
        return False

if __name__ == '__main__':
    arquivos = [
        'baixar_asaas_json.py',
        'importar_json_banco.py'
    ]
    
    print('Removendo emojis dos arquivos...')
    print('='*60)
    
    for arquivo in arquivos:
        remover_emojis_arquivo(arquivo)
    
    print('='*60)
    print('[OK] Processo concluido!')
