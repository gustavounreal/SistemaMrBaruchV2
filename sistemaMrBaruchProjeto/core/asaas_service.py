import requests
import logging
import json
from django.conf import settings
from django.utils import timezone
from .models import LogSistema
from .services import LogService, ConfiguracaoService

logger = logging.getLogger(__name__)

class AsaasService:
    """
    Serviço centralizado para integração com a API ASAAS
    """
    
    def __init__(self):
        # FORÇAR SEMPRE PRODUÇÃO
        self.base_url = getattr(settings, 'ASAAS_API_URL', 'https://api.asaas.com/v3')
        self.api_token = getattr(settings, 'ASAAS_API_TOKEN', '')
        # Preferir valores do banco (painel), com fallback para settings
        self.max_retries = int(
            ConfiguracaoService.obter_config('ASAAS_MAX_RETRIES', getattr(settings, 'ASAAS_MAX_RETRIES', 3)) or 3
        )
        self.timeout = int(
            ConfiguracaoService.obter_config('ASAAS_TIMEOUT', getattr(settings, 'ASAAS_TIMEOUT', 30)) or 30
        )
        
        self.headers = {
            'Content-Type': 'application/json',
            'access_token': self.api_token
        }
    
    def _fazer_requisicao(self, metodo, endpoint, dados=None, params=None):
        """
        Método interno para fazer requisições à API ASAAS
        """
        url = f"{self.base_url}/{endpoint}"
        last_error_text = None
        
        for tentativa in range(self.max_retries):
            try:
                response = requests.request(
                    method=metodo,
                    url=url,
                    json=dados,
                    params=params,
                    headers=self.headers,
                    timeout=self.timeout
                )
                
                # Log da requisição
                LogService.registrar(
                    nivel='INFO' if response.status_code in [200, 201] else 'WARNING',
                    mensagem=f"ASAAS {metodo} {endpoint} - Status: {response.status_code}",
                    modulo='core',
                    acao='asaas_request'
                )
                
                if response.status_code in [200, 201]:
                    return response.json()
                else:
                    logger.warning(f"Tentativa {tentativa + 1} falhou: {response.status_code} - {response.text}")
                    last_error_text = response.text
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Erro de conexão na tentativa {tentativa + 1}: {str(e)}")
                last_error_text = str(e)
                
            except Exception as e:
                logger.error(f"Erro inesperado na tentativa {tentativa + 1}: {str(e)}")
                last_error_text = str(e)
        
        # Se todas as tentativas falharem
        LogService.registrar(
            nivel='ERROR',
            mensagem=f"Falha após {self.max_retries} tentativas - {metodo} {endpoint}",
            modulo='core',
            acao='asaas_request_failed'
        )

        if last_error_text:
            try:
                return json.loads(last_error_text)
            except Exception:
                return {'errors': [{'description': last_error_text}]}
        
        return None
    
    # ========== CLIENTES ==========
    
    def criar_cliente(self, dados_cliente):
        """
        Cria um cliente no ASAAS
        """
        payload = {
            "name": dados_cliente.get('nome'),
            "cpfCnpj": dados_cliente.get('cpf_cnpj'),
            "email": dados_cliente.get('email'),
            "phone": dados_cliente.get('telefone'),
            "mobilePhone": dados_cliente.get('telefone'),
            "postalCode": dados_cliente.get('cep'),
            "address": dados_cliente.get('endereco'),
            "addressNumber": dados_cliente.get('numero'),
            "complement": dados_cliente.get('complemento', ''),
            "province": dados_cliente.get('bairro'),
            "externalReference": dados_cliente.get('id_cliente'),
            "notificationDisabled": True,
            "additionalEmails": "",
            "municipalInscription": dados_cliente.get('inscricao_municipal', ''),
            "stateInscription": dados_cliente.get('inscricao_estadual', ''),
            "observations": "Cliente do sistema Mr. Baruch",
            "foreignCustomer": False
        }
        
        return self._fazer_requisicao('POST', 'customers', payload)
    
    def obter_cliente(self, customer_id):
        """Obtém dados de um cliente no ASAAS"""
        return self._fazer_requisicao('GET', f'customers/{customer_id}')
    
    def atualizar_cliente(self, customer_id, dados_cliente):
        """Atualiza um cliente no ASAAS"""
        return self._fazer_requisicao('PUT', f'customers/{customer_id}', dados_cliente)
    
    def excluir_cliente(self, customer_id):
        """Exclui um cliente no ASAAS"""
        return self._fazer_requisicao('DELETE', f'customers/{customer_id}')
    
    # ========== COBRANÇAS ==========
    
    def criar_cobranca(self, dados_cobranca):
        """
        Cria uma cobrança no ASAAS
        """
        # Valor da cobrança (fallback para config PIX_VALOR_LEVANTAMENTO quando não informado)
        valor_informado = dados_cobranca.get('value')
        if valor_informado in (None, '', 0, '0', '0.0'):
            valor_informado = ConfiguracaoService.obter_config('PIX_VALOR_LEVANTAMENTO', 5.00)
        
        # ASAAS exige valor mínimo de R$ 5,00 por parcela/cobrança
        valor_informado = float(valor_informado)
        if valor_informado < 5.00:
            logger.warning(f"Valor {valor_informado} abaixo do mínimo ASAAS. Ajustando para R$ 5,00")
            valor_informado = 5.00
        
        descricao = dados_cobranca.get('description') or ConfiguracaoService.obter_config('PIX_DESCRICAO', 'Levantamento de informações (PIX)')

        payload = {
            "customer": dados_cobranca.get('customer_id'),
            "billingType": dados_cobranca.get('billing_type', 'BOLETO'),  # BOLETO, PIX, CREDIT_CARD
            "dueDate": dados_cobranca.get('due_date'),
            "value": valor_informado,
            "description": descricao,
            "externalReference": dados_cobranca.get('external_reference'),
            "installmentCount": dados_cobranca.get('installment_count', 1),
            "totalValue": float(dados_cobranca.get('total_value', valor_informado)),
        }
        
        # Campos específicos para PIX
        if dados_cobranca.get('billing_type') == 'PIX':
            payload.update({
                "dueDate": timezone.now().date().isoformat(),  # PIX vence no mesmo dia
            })
        
        return self._fazer_requisicao('POST', 'payments', payload)
    
    def criar_cobranca_parcelada(self, dados_cobranca):
        """
        Cria cobrança parcelada no ASAAS
        """
        valor_total = float(dados_cobranca.get('total_value'))
        numero_parcelas = dados_cobranca.get('installment_count', 1)
        valor_parcela = float(dados_cobranca.get('value'))
        
        # ASAAS exige valor mínimo de R$ 5,00 por parcela
        if valor_parcela < 5.00:
            logger.warning(f"Valor da parcela {valor_parcela} abaixo do mínimo ASAAS. Ajustando para R$ 5,00")
            valor_parcela = 5.00
            valor_total = valor_parcela * numero_parcelas
        
        payload = {
            "customer": dados_cobranca.get('customer_id'),
            "billingType": "BOLETO",
            "dueDate": dados_cobranca.get('due_date'),
            "value": valor_parcela,
            "description": dados_cobranca.get('description', ''),
            "externalReference": dados_cobranca.get('external_reference'),
            "installmentCount": numero_parcelas,
            "totalValue": valor_total,
        }
        
        return self._fazer_requisicao('POST', 'payments', payload)
    
    def obter_cobranca(self, payment_id):
        """Obtém dados de uma cobrança"""
        return self._fazer_requisicao('GET', f'payments/{payment_id}')
    
    def obter_qr_code_pix(self, payment_id):
        """Obtém QR Code para pagamento PIX"""
        return self._fazer_requisicao('GET', f'payments/{payment_id}/pixQrCode')
    
    def atualizar_cobranca(self, payment_id, dados_cobranca):
        """Atualiza uma cobrança"""
        return self._fazer_requisicao('PUT', f'payments/{payment_id}', dados_cobranca)
    
    def excluir_cobranca(self, payment_id):
        """Exclui uma cobrança"""
        return self._fazer_requisicao('DELETE', f'payments/{payment_id}')
    
    def estornar_cobranca(self, payment_id):
        """Estorna uma cobrança paga"""
        return self._fazer_requisicao('POST', f'payments/{payment_id}/refund')
    
    # ========== ASSINATURAS ==========
    
    def criar_assinatura(self, dados_assinatura):
        """
        Cria uma assinatura recorrente
        """
        payload = {
            "customer": dados_assinatura.get('customer_id'),
            "billingType": dados_assinatura.get('billing_type', 'BOLETO'),
            "value": float(dados_assinatura.get('value')),
            "nextDueDate": dados_assinatura.get('next_due_date'),
            "cycle": dados_assinatura.get('cycle', 'MONTHLY'),  # WEEKLY, BIWEEKLY, MONTHLY
            "description": dados_assinatura.get('description', ''),
            "externalReference": dados_assinatura.get('external_reference'),
        }
        
        return self._fazer_requisicao('POST', 'subscriptions', payload)
    
    # ========== FINANCEIRO ==========
    
    def obter_saldo(self):
        """Consulta saldo da conta"""
        return self._fazer_requisicao('GET', 'finance/balance')
    
    def obter_transacoes(self, start_date=None, end_date=None, offset=0, limit=100):
        """Obtém extrato de transações"""
        params = {
            'offset': offset,
            'limit': limit
        }
        
        if start_date:
            params['startDate'] = start_date
        if end_date:
            params['endDate'] = end_date
            
        return self._fazer_requisicao('GET', 'financialTransactions', params=params)
    
    # ========== WEBHOOKS ==========
    
    def criar_webhook(self, url_webhook):
        """
        Configura webhook para notificações
        """
        payload = {
            "url": url_webhook,
            "email": "sistema@mrbaruch.com.br",
            "interrupted": False,
            "enabled": True,
            "apiVersion": 3
        }
        
        return self._fazer_requisicao('POST', 'webhooks', payload)
    
    # ========== UTILITÁRIOS ==========
    
    def validar_configuracao(self):
        """
        Valida se a configuração do ASAAS está funcionando
        """
        try:
            resposta = self.obter_saldo()
            return resposta is not None and 'balance' in resposta
        except Exception as e:
            logger.error(f"Erro ao validar configuração ASAAS: {str(e)}")
            return False

    def diagnosticar_configuracao(self):
        """
        Executa um diagnóstico completo da integração ASAAS, retornando detalhes dos testes.
        Não expõe segredos (token completo).
        """
        detalhes = {
            'ok': False,
            'executado_em': timezone.now(),
            'config': {
                'base_url': self.base_url,
                'timeout': self.timeout,
                'max_retries': self.max_retries,
                'token_configurado': bool(self.api_token),
            },
            'checks': []
        }
        # Check 1: Token configurado
        token_ok = bool(self.api_token)
        detalhes['checks'].append({
            'nome': 'Token configurado',
            'status': token_ok,
            'detalhe': 'Token presente nas configurações' if token_ok else 'Token ausente; configure ASAAS_API_TOKEN'
        })

        # Check 2: Consulta de saldo
        try:
            saldo_resp = self.obter_saldo()
            saldo_ok = isinstance(saldo_resp, dict) and 'balance' in saldo_resp
            detalhes['checks'].append({
                'nome': 'Consulta de saldo (finance/balance)',
                'status': saldo_ok,
                'detalhe': f"Resposta contém 'balance'" if saldo_ok else f"Resposta inválida: {str(saldo_resp)[:120]}"
            })
        except Exception as e:
            detalhes['checks'].append({
                'nome': 'Consulta de saldo (finance/balance)',
                'status': False,
                'detalhe': f'Erro: {str(e)}'
            })

        detalhes['ok'] = all(c['status'] for c in detalhes['checks'])
        return detalhes

    def formatar_dados_lead(self, lead):
        """
        Formata dados do modelo Lead para o ASAAS
        """
        return {
            'nome': getattr(lead, 'nome_completo', ''),
            'cpf_cnpj': getattr(lead, 'cpf_cnpj', ''),
            'email': getattr(lead, 'email', ''),
            'telefone': getattr(lead, 'telefone', ''),
            'cep': getattr(lead, 'cep', ''),
            'endereco': getattr(lead, 'rua', ''),
            'numero': getattr(lead, 'numero', ''),
            'bairro': getattr(lead, 'bairro', ''),
            'id_cliente': str(lead.id)
        }
# Instância global do serviço
asaas_service = AsaasService()