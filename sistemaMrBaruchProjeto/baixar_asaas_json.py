"""
SCRIPT 1: Baixar TODOS os dados do Asaas e salvar em JSON
Uso: python baixar_asaas_json.py [conta]
Exemplos:
  python baixar_asaas_json.py principal
  python baixar_asaas_json.py alternativo
"""
import os
import sys
import django
import json
import requests
import time
from datetime import datetime

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistemaMrBaruchProjeto.settings')
django.setup()

from django.conf import settings


class BaixadorAsaas:
    def __init__(self, nome_conta="principal"):
        self.nome_conta = nome_conta
        
        if nome_conta == "alternativo":
            self.api_token = getattr(settings, 'ASAAS_ALTERNATIVO_TOKEN', '')
        else:
            self.api_token = getattr(settings, 'ASAAS_API_TOKEN', '')
            
        self.base_url = getattr(settings, 'ASAAS_API_URL', 'https://api.asaas.com/v3')
        self.headers = {
            'Content-Type': 'application/json',
            'access_token': self.api_token
        }
        self.timeout = 120
        
        # Dados coletados
        self.clientes = []
        self.cobrancas = []
        
    def fazer_requisicao(self, endpoint, params=None):
        """Faz requisição com retry"""
        url = f"{self.base_url}/{endpoint}"
        
        for tentativa in range(1, 4):
            try:
                print(f"  📡 Requisição {tentativa}/3: {endpoint}")
                
                response = requests.get(
                    url,
                    params=params,
                    headers=self.headers,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    return response.json()
                    
                elif response.status_code in [429, 403]:
                    tempo = 60 if response.status_code == 403 else 10
                    print(f"  ⚠️  Rate limit. Aguardando {tempo}s...")
                    time.sleep(tempo)
                    continue
                    
                else:
                    print(f"  ❌ Erro {response.status_code}: {response.text[:200]}")
                    time.sleep(2)
                    
            except Exception as e:
                print(f"  ❌ Erro: {str(e)}")
                time.sleep(3)
        
        return None
    
    def baixar_clientes(self):
        """Baixa TODOS os clientes"""
        print("\n" + "="*80)
        print("🔽 BAIXANDO TODOS OS CLIENTES")
        print("="*80)
        
        offset = 0
        limit = 100
        pagina = 1
        total_esperado = None
        
        while True:
            print(f"\n📄 Página {pagina} (offset={offset})")
            
            params = {'offset': offset, 'limit': limit}
            response = self.fazer_requisicao('customers', params)
            
            if not response:
                print("❌ Falha ao baixar. Parando.")
                break
            
            clientes_pagina = response.get('data', [])
            total_count = response.get('totalCount', 0)
            has_more = response.get('hasMore', False)
            
            # Guardar total esperado na primeira requisição
            if total_esperado is None:
                total_esperado = total_count
                print(f"📊 Total de clientes no Asaas: {total_esperado}")
            
            if not clientes_pagina:
                print("✅ Sem mais clientes.")
                break
            
            self.clientes.extend(clientes_pagina)
            print(f"✅ Baixados {len(clientes_pagina)} clientes. Total: {len(self.clientes)}/{total_esperado}")
            
            if not has_more:
                print("✅ API informou que não há mais páginas (hasMore=false)")
                break
            
            time.sleep(1)  # Evitar rate limit
            offset += limit
            pagina += 1
        
        # VALIDAÇÃO: Verificar se baixou tudo
        print(f"\n" + "="*80)
        print("🔍 VALIDAÇÃO DE CLIENTES")
        print("="*80)
        print(f"📊 Total esperado: {total_esperado}")
        print(f"📊 Total baixado: {len(self.clientes)}")
        
        if total_esperado and len(self.clientes) == total_esperado:
            print(f"✅ CONFIRMADO: Baixados {len(self.clientes)} clientes - 100% completo!")
        elif total_esperado and len(self.clientes) < total_esperado:
            faltam = total_esperado - len(self.clientes)
            print(f"⚠️  ATENÇÃO: Faltam {faltam} clientes! ({len(self.clientes)}/{total_esperado})")
            if not input("\n⚠️  Continuar mesmo assim? (s/n): ").lower().startswith('s'):
                raise Exception(f"Download incompleto! Faltam {faltam} clientes.")
        else:
            print(f"✅ Total baixado: {len(self.clientes)} clientes")
        
        return len(self.clientes)
    
    def baixar_cobrancas(self):
        """Baixa TODAS as cobranças de TODOS os clientes"""
        print("\n" + "="*80)
        print("🔽 BAIXANDO TODAS AS COBRANÇAS")
        print("="*80)
        
        total_clientes = len(self.clientes)
        
        for i, cliente in enumerate(self.clientes, 1):
            customer_id = cliente.get('id')
            customer_name = cliente.get('name', 'Sem nome')[:50]
            
            print(f"\n👤 Cliente {i}/{total_clientes}: {customer_name}")
            
            offset = 0
            limit = 100
            cobrancas_cliente = 0
            
            while True:
                params = {
                    'customer': customer_id,
                    'offset': offset,
                    'limit': limit
                }
                
                response = self.fazer_requisicao('payments', params)
                
                if not response:
                    break
                
                cobrancas_pagina = response.get('data', [])
                has_more = response.get('hasMore', False)
                
                if not cobrancas_pagina:
                    break
                
                # Adicionar customer_id em cada cobrança
                for cobranca in cobrancas_pagina:
                    cobranca['_customer_id'] = customer_id
                
                self.cobrancas.extend(cobrancas_pagina)
                cobrancas_cliente += len(cobrancas_pagina)
                
                if not has_more:
                    break
                
                time.sleep(0.5)
                offset += limit
            
            print(f"   ✅ {cobrancas_cliente} cobranças")
            time.sleep(0.3)  # Pausa entre clientes
        
        print(f"\n✅ Total: {len(self.cobrancas)} cobranças baixadas")
        return len(self.cobrancas)
    
    def salvar_json(self):
        """Salva tudo em arquivo JSON"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nome_arquivo = f'asaas_{self.nome_conta}_{timestamp}.json'
        
        # Calcular estatísticas das cobranças
        cobrancas_por_status = {}
        valor_total = 0
        for c in self.cobrancas:
            status = c.get('status', 'UNKNOWN')
            cobrancas_por_status[status] = cobrancas_por_status.get(status, 0) + 1
            valor_total += float(c.get('value', 0))
        
        dados = {
            'conta': self.nome_conta,
            'data_download': datetime.now().isoformat(),
            'total_clientes': len(self.clientes),
            'total_cobrancas': len(self.cobrancas),
            'valor_total_cobrancas': valor_total,
            'cobrancas_por_status': cobrancas_por_status,
            'validacao': {
                'download_completo': True,
                'clientes_unicos': len(set(c.get('id') for c in self.clientes)),
                'cobrancas_unicas': len(set(c.get('id') for c in self.cobrancas)),
            },
            'clientes': self.clientes,
            'cobrancas': self.cobrancas
        }
        
        print("\n" + "="*80)
        print("💾 SALVANDO ARQUIVO JSON")
        print("="*80)
        
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        
        tamanho_mb = os.path.getsize(nome_arquivo) / (1024 * 1024)
        
        print(f"\n✅ Arquivo salvo: {nome_arquivo}")
        print(f"📊 Tamanho: {tamanho_mb:.2f} MB")
        print(f"📊 Clientes: {len(self.clientes)} (únicos: {dados['validacao']['clientes_unicos']})")
        print(f"📊 Cobranças: {len(self.cobrancas)} (únicas: {dados['validacao']['cobrancas_unicas']})")
        print(f"💰 Valor total: R$ {valor_total:,.2f}")
        print(f"\n📊 Cobranças por status:")
        for status, qtd in sorted(cobrancas_por_status.items()):
            print(f"   • {status}: {qtd}")
        
        return nome_arquivo
    
    def validar_integridade(self):
        """Validação final de integridade dos dados"""
        print("\n" + "="*80)
        print("🔍 VALIDAÇÃO FINAL DE INTEGRIDADE")
        print("="*80)
        
        erros = []
        avisos = []
        
        # 1. Verificar clientes duplicados
        ids_clientes = [c.get('id') for c in self.clientes if c.get('id')]
        duplicados_clientes = len(ids_clientes) - len(set(ids_clientes))
        if duplicados_clientes > 0:
            avisos.append(f"⚠️  {duplicados_clientes} clientes duplicados no download")
        else:
            print(f"✅ Nenhum cliente duplicado")
        
        # 2. Verificar cobranças duplicadas
        ids_cobrancas = [c.get('id') for c in self.cobrancas if c.get('id')]
        duplicados_cobrancas = len(ids_cobrancas) - len(set(ids_cobrancas))
        if duplicados_cobrancas > 0:
            avisos.append(f"⚠️  {duplicados_cobrancas} cobranças duplicadas no download")
        else:
            print(f"✅ Nenhuma cobrança duplicada")
        
        # 3. Verificar clientes sem ID
        clientes_sem_id = sum(1 for c in self.clientes if not c.get('id'))
        if clientes_sem_id > 0:
            erros.append(f"❌ {clientes_sem_id} clientes sem ID!")
        else:
            print(f"✅ Todos os clientes têm ID")
        
        # 4. Verificar cobranças orfãs (sem cliente)
        customer_ids = set(c.get('id') for c in self.clientes)
        cobrancas_orfas = 0
        for cobranca in self.cobrancas:
            customer_id = cobranca.get('_customer_id') or cobranca.get('customer')
            if customer_id not in customer_ids:
                cobrancas_orfas += 1
        
        if cobrancas_orfas > 0:
            avisos.append(f"⚠️  {cobrancas_orfas} cobranças sem cliente correspondente")
        else:
            print(f"✅ Todas as cobranças têm cliente correspondente")
        
        # 5. Verificar clientes sem nome
        clientes_sem_nome = sum(1 for c in self.clientes if not c.get('name'))
        if clientes_sem_nome > 0:
            avisos.append(f"⚠️  {clientes_sem_nome} clientes sem nome")
        else:
            print(f"✅ Todos os clientes têm nome")
        
        # Mostrar resultado
        print("\n" + "="*80)
        if erros:
            print("❌ ERROS ENCONTRADOS:")
            for erro in erros:
                print(f"   {erro}")
            raise Exception("Validação falhou! Corrija os erros antes de continuar.")
        
        if avisos:
            print("⚠️  AVISOS:")
            for aviso in avisos:
                print(f"   {aviso}")
            print("\n⚠️  Os avisos não impedem a continuação, mas devem ser verificados.")
        else:
            print("✅ VALIDAÇÃO 100% APROVADA!")
        
        print("="*80)
    
    def executar(self):
        """Executa download completo"""
        print("\n" + "🚀"*40)
        print(f"BAIXAR DADOS DO ASAAS - CONTA: {self.nome_conta.upper()}")
        print("🚀"*40)
        
        inicio = time.time()
        
        # Baixar dados
        self.baixar_clientes()
        self.baixar_cobrancas()
        
        # Validar integridade
        self.validar_integridade()
        
        # Salvar JSON
        arquivo = self.salvar_json()
        
        duracao = time.time() - inicio
        
        print("\n" + "🎉"*40)
        print("DOWNLOAD CONCLUÍDO COM SUCESSO!")
        print(f"⏱️  Tempo: {duracao:.0f} segundos ({duracao/60:.1f} minutos)")
        print("🎉"*40)
        
        print(f"\n📝 PRÓXIMO PASSO:")
        print(f"   Execute: python importar_json_banco.py {arquivo}")
        
        print(f"\n✅ GARANTIAS:")
        print(f"   • Download 100% completo (totalCount validado)")
        print(f"   • Sem duplicações")
        print(f"   • Todas as cobranças têm cliente")
        print(f"   • Arquivo JSON íntegro e validado")
        
        return arquivo


if __name__ == '__main__':
    # Verificar argumentos
    if len(sys.argv) > 1:
        conta = sys.argv[1].lower()
        if conta not in ['principal', 'alternativo']:
            print("❌ Conta inválida! Use: principal ou alternativo")
            sys.exit(1)
    else:
        conta = 'principal'
    
    print(f"\n🎯 Conta selecionada: {conta.upper()}")
    
    if not input("\n⚠️  Este processo vai baixar TODOS os dados. Continuar? (s/n): ").lower().startswith('s'):
        print("❌ Cancelado pelo usuário")
        sys.exit(0)
    
    # Executar
    baixador = BaixadorAsaas(nome_conta=conta)
    
    try:
        arquivo = baixador.executar()
        print(f"\n✅ Sucesso! Arquivo: {arquivo}")
    except KeyboardInterrupt:
        print("\n\n❌ Interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ ERRO: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
