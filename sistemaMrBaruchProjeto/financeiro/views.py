from financeiro.models import ClienteAsaas
from core.asaas_service import asaas_service
import logging

logger = logging.getLogger(__name__)

def criar_cliente_asaas(lead):
    """Cria um cliente no Asaas e salva na tabela ClienteAsaas"""
    logger.info(f"Iniciando criação de cliente ASAAS para lead {lead.id}")
    
    # Verificar se já existe um cliente ASAAS para este lead
    cliente_existente = ClienteAsaas.objects.filter(lead=lead).first()
    if cliente_existente:
        logger.info(f"Cliente ASAAS já existe para lead {lead.id}: {cliente_existente.asaas_customer_id}")
        return cliente_existente
    
    # Validar CPF/CNPJ obrigatório
    if not lead.cpf_cnpj:
        logger.error(f"Lead {lead.id} sem CPF/CNPJ")
        raise ValueError("CPF ou CNPJ é obrigatório para criar um cliente no Asaas.")
    
    # Preparar dados do cliente
    cliente_data = {
        'nome': lead.nome_completo,
        'email': lead.email if lead.email else 'naotem@email.com',  # Email obrigatório no ASAAS
        'telefone': lead.telefone if lead.telefone else '',
        'cpf_cnpj': lead.cpf_cnpj, 
    }
    
    logger.info(f"Enviando dados para ASAAS - Lead {lead.id}: Nome={cliente_data['nome']}, CPF={cliente_data['cpf_cnpj']}")
    
    # Criar cliente no ASAAS
    response = asaas_service.criar_cliente(cliente_data)
    
    if response and 'id' in response:
        # Criar registro na tabela ClienteAsaas
        cliente_asaas = ClienteAsaas.objects.create(
            lead=lead,
            asaas_customer_id=response['id']
        )
        logger.info(f"Cliente ASAAS criado com sucesso: {response['id']} para lead {lead.id}")
        return cliente_asaas
    else:
        error_msg = "Erro ao criar cliente no ASAAS"
        if response and 'errors' in response:
            error_msg = response['errors'][0].get('description', error_msg)
        logger.error(f"Falha ao criar cliente ASAAS para lead {lead.id}: {error_msg}")
        logger.error(f"Response completa do ASAAS: {response}")
        raise ValueError(error_msg)