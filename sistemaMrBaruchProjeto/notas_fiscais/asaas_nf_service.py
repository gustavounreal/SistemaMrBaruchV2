"""
Serviço para emissão de Notas Fiscais via API do Asaas
"""

import requests
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class AsaasNFService:
    """
    Serviço para integração com API de Notas Fiscais do Asaas
    Documentação: https://docs.asaas.com/reference/emissao-de-notas-fiscais
    """
    
    # URLs da API
    BASE_URL_PRODUCTION = "https://api.asaas.com/v3"
    
    def __init__(self, use_sandbox=False):
        """
        Inicializa o serviço
        
        Args:
            use_sandbox: OBSOLETO - Sempre usa PRODUÇÃO
        """
        # Pegar token do settings (ASAAS_API_TOKEN)
        self.api_key = getattr(settings, 'ASAAS_API_TOKEN', '')
        
        # FORÇAR SEMPRE PRODUÇÃO
        self.base_url = getattr(settings, 'ASAAS_API_URL', self.BASE_URL_PRODUCTION)
        
        self.headers = {
            'access_token': self.api_key,
            'Content-Type': 'application/json'
        }
        
        print(f"[AsaasNF] Inicializado - Base URL: {self.base_url}")
        print(f"[AsaasNF] API Key (primeiros 20 chars): {self.api_key[:20]}...")
    
    def validar_dados_emissao(self, venda):
        """
        Valida se todos os dados necessários para emissão estão presentes
        
        Args:
            venda: Objeto Venda
            
        Returns:
            tuple: (bool, list) - (é_valido, lista_de_erros)
        """
        erros = []
        
        # Validar dados do lead
        if not venda.cliente or not venda.cliente.lead:
            erros.append("Cliente/Lead não encontrado")
            return False, erros
        
        lead = venda.cliente.lead
        cliente = venda.cliente
        
        # CPF/CNPJ obrigatório
        if not lead.cpf_cnpj:
            erros.append("CPF/CNPJ não cadastrado")
        
        # E-mail obrigatório
        if not lead.email and not venda.nf_email:
            erros.append("E-mail não cadastrado")
        
        # Nome obrigatório
        if not lead.nome_completo:
            erros.append("Nome do cliente não cadastrado")
        
        # Endereço completo obrigatório
        campos_endereco = {
            'CEP': cliente.cep,
            'Rua': cliente.rua,
            'Número': cliente.numero,
            'Bairro': cliente.bairro,
            'Cidade': cliente.cidade,
            'Estado': cliente.estado,
        }
        
        for campo, valor in campos_endereco.items():
            if not valor:
                erros.append(f"Endereço incompleto: {campo} não cadastrado")
        
        # Se for PJ, validar Razão Social
        if venda.nf_tipo_pessoa == 'PJ':
            if not cliente.razao_social:
                erros.append("Razão Social não cadastrada (obrigatório para CNPJ)")
        
        # Validar serviço
        if not venda.servico:
            erros.append("Serviço não vinculado à venda")
        
        return len(erros) == 0, erros
    
    def preparar_payload(self, venda, tipo='ENTRADA', parcela=None):
        """
        Prepara o payload para enviar à API do Asaas
        
        Args:
            venda: Objeto Venda
            tipo: 'ENTRADA' ou 'PARCELA'
            parcela: Objeto Parcela (se tipo='PARCELA')
            
        Returns:
            dict: Payload formatado para API
        """
        from .models import ConfiguracaoFiscal
        
        lead = venda.cliente.lead
        cliente = venda.cliente
        
        # Buscar configurações fiscais
        try:
            config = ConfiguracaoFiscal.objects.first()
        except:
            config = None
        
        # Determinar valor e ID de pagamento
        if tipo == 'ENTRADA':
            valor = float(venda.valor_entrada)
            # Assumindo que existe um campo id_asaas_entrada na venda
            # Se não existir, precisaremos adicionar
            id_pagamento_asaas = getattr(venda, 'id_asaas_entrada', '')
        else:
            valor = float(parcela.valor)
            id_pagamento_asaas = parcela.id_asaas
        
        # Descrição do serviço
        descricao = f"Consultoria Financeira - {venda.servico.nome}"
        if config and config.descricao_servico_padrao:
            descricao = config.descricao_servico_padrao
        
        # Código de serviço
        codigo_servico = "01.01"  # Padrão: Análise e desenvolvimento de sistemas
        if config and config.codigo_servico_padrao:
            codigo_servico = config.codigo_servico_padrao
        
        # Alíquota ISS
        aliquota_iss = 2.00
        if config and config.aliquota_iss_padrao:
            aliquota_iss = float(config.aliquota_iss_padrao)
        
        # Montar payload conforme documentação Asaas
        payload = {
            "payment": id_pagamento_asaas,
            "serviceDescription": descricao,
            "observations": f"Venda #{venda.id} - {tipo}",
            
            # Dados do tomador (cliente)
            "customer": {
                "name": lead.nome_completo,
                "email": venda.nf_email or lead.email,
                "cpfCnpj": lead.cpf_cnpj,
                "phone": lead.telefone or "",
                "address": {
                    "postalCode": cliente.cep.replace('-', ''),
                    "addressLine1": cliente.rua,
                    "addressNumber": cliente.numero,
                    "neighborhood": cliente.bairro,
                    "city": cliente.cidade,
                    "state": cliente.estado,
                },
            },
            
            # Valor da nota
            "value": valor,
            
            # Impostos (Simples Nacional)
            "taxes": {
                "retainIss": False,  # Simples Nacional não retém ISS
                "iss": aliquota_iss,
                "cofins": 0,
                "csll": 0,
                "inss": 0,
                "ir": 0,
                "pis": 0,
            },
            
            # Código de serviço municipal
            "municipalServiceCode": codigo_servico,
            "municipalServiceName": "Consultoria e Assessoria",
        }
        
        # Se for Pessoa Jurídica
        if venda.nf_tipo_pessoa == 'PJ' and cliente.razao_social:
            payload["customer"]["companyName"] = cliente.razao_social
            
            if cliente.inscricao_municipal:
                payload["customer"]["municipalInscription"] = cliente.inscricao_municipal
        
        return payload
    
    def emitir_nf(self, venda, tipo='ENTRADA', parcela=None):
        """
        Emite nota fiscal via API do Asaas
        
        Args:
            venda: Objeto Venda
            tipo: 'ENTRADA' ou 'PARCELA'
            parcela: Objeto Parcela (se tipo='PARCELA')
            
        Returns:
            dict: Resultado da operação
                {
                    'success': bool,
                    'data': dict (se sucesso),
                    'erro': str (se falha),
                    'id_nf_asaas': str,
                    'numero_nf': str,
                    'url_pdf': str,
                    'url_xml': str,
                }
        """
        logger.info(f"[AsaasNF] Iniciando emissão de NF para Venda #{venda.id} - Tipo: {tipo}")
        
        # 1. Validar dados
        is_valid, erros = self.validar_dados_emissao(venda)
        if not is_valid:
            logger.error(f"[AsaasNF] Validação falhou: {erros}")
            return {
                'success': False,
                'erro': f"Dados incompletos: {', '.join(erros)}",
                'erros': erros
            }
        
        # 2. Preparar payload
        try:
            payload = self.preparar_payload(venda, tipo, parcela)
        except Exception as e:
            logger.error(f"[AsaasNF] Erro ao preparar payload: {str(e)}")
            return {
                'success': False,
                'erro': f"Erro ao preparar dados: {str(e)}"
            }
        
        # 3. Fazer requisição à API
        url = f"{self.base_url}/invoices"
        
        try:
            logger.info(f"[AsaasNF] Enviando requisição para {url}")
            logger.debug(f"[AsaasNF] Payload: {payload}")
            
            response = requests.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=30
            )
            
            logger.info(f"[AsaasNF] Status da resposta: {response.status_code}")
            
            # Processar resposta
            if response.status_code in [200, 201]:
                data = response.json()
                logger.info(f"[AsaasNF] Nota fiscal emitida com sucesso: {data.get('number')}")
                
                return {
                    'success': True,
                    'data': data,
                    'id_nf_asaas': data.get('id'),
                    'numero_nf': data.get('number'),
                    'serie_nf': data.get('series'),
                    'codigo_verificacao': data.get('verificationCode'),
                    'chave_acesso': data.get('accessKey'),
                    'url_pdf': data.get('pdfUrl'),
                    'url_xml': data.get('xmlUrl'),
                    'status_asaas': data.get('status'),
                }
            else:
                error_text = response.text
                logger.error(f"[AsaasNF] Erro na API: {response.status_code} - {error_text}")
                
                try:
                    error_data = response.json()
                    error_message = error_data.get('errors', [{}])[0].get('description', error_text)
                except:
                    error_message = error_text
                
                return {
                    'success': False,
                    'erro': f"Erro {response.status_code}: {error_message}",
                    'status_code': response.status_code,
                    'response': error_text
                }
        
        except requests.exceptions.Timeout:
            logger.error("[AsaasNF] Timeout na requisição")
            return {
                'success': False,
                'erro': "Timeout: A API do Asaas demorou muito para responder"
            }
        
        except requests.exceptions.ConnectionError:
            logger.error("[AsaasNF] Erro de conexão")
            return {
                'success': False,
                'erro': "Erro de conexão com a API do Asaas"
            }
        
        except Exception as e:
            logger.error(f"[AsaasNF] Erro inesperado: {str(e)}")
            return {
                'success': False,
                'erro': f"Erro inesperado: {str(e)}"
            }
    
    def consultar_nf(self, id_nf_asaas):
        """
        Consulta status de uma nota fiscal no Asaas
        
        Args:
            id_nf_asaas: ID da nota no Asaas
            
        Returns:
            dict: Resultado da consulta
        """
        url = f"{self.base_url}/invoices/{id_nf_asaas}"
        
        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'data': data,
                    'status': data.get('status'),
                    'numero_nf': data.get('number'),
                }
            else:
                return {
                    'success': False,
                    'erro': f"Erro {response.status_code}: {response.text}"
                }
        
        except Exception as e:
            return {
                'success': False,
                'erro': str(e)
            }
    
    def cancelar_nf(self, id_nf_asaas, motivo):
        """
        Cancela uma nota fiscal no Asaas
        
        Args:
            id_nf_asaas: ID da nota no Asaas
            motivo: Motivo do cancelamento
            
        Returns:
            dict: Resultado do cancelamento
        """
        url = f"{self.base_url}/invoices/{id_nf_asaas}"
        
        payload = {
            "cancelDescription": motivo
        }
        
        try:
            response = requests.delete(
                url,
                json=payload,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code in [200, 204]:
                logger.info(f"[AsaasNF] Nota {id_nf_asaas} cancelada com sucesso")
                return {
                    'success': True,
                    'data': response.json() if response.status_code == 200 else None
                }
            else:
                logger.error(f"[AsaasNF] Erro ao cancelar: {response.text}")
                return {
                    'success': False,
                    'erro': f"Erro {response.status_code}: {response.text}"
                }
        
        except Exception as e:
            logger.error(f"[AsaasNF] Erro ao cancelar: {str(e)}")
            return {
                'success': False,
                'erro': str(e)
            }
