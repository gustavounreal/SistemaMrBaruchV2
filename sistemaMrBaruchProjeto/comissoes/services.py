"""
Serviço de Geração e Gestão de Comissões
Responsável por:
- Gerar comissões automaticamente quando pagamentos são confirmados
- Autorizar comissões
- Processar pagamentos
- Cancelar comissões
"""

from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum
from .models import ComissaoLead, ComissaoConsultor, ComissaoCaptador
from core.models import ConfiguracaoSistema


def gerar_comissao_levantamento(lead, atendente):
    """
    Gera comissão para atendente quando levantamento de lead é pago
    
    Args:
        lead: Instância do Lead
        atendente: Usuário atendente
        
    Returns:
        ComissaoLead criada ou None se já existir
    """
    # Verifica se já existe comissão para este lead
    comissao_existente = ComissaoLead.objects.filter(lead=lead, atendente=atendente).first()
    if comissao_existente:
        return comissao_existente
    
    # Busca valor configurado
    valor_comissao = ComissaoLead.obter_valor_comissao()
    
    # Define competência como mês atual
    competencia = timezone.now().date().replace(day=1)
    
    # Cria a comissão
    comissao = ComissaoLead.objects.create(
        lead=lead,
        atendente=atendente,
        valor=valor_comissao,
        status='DISPONIVEL',
        competencia=competencia
    )
    
    return comissao


def gerar_comissao_venda_consultor(venda, entrada_paga=False):
    """
    Gera comissão para consultor quando a ENTRADA da venda é paga
    
    REGRA: Comissão calculada SOMENTE sobre o valor da ENTRADA
    Percentual progressivo por faturamento mensal total do consultor
    
    Args:
        venda: Instância da Venda
        entrada_paga: Boolean indicando se a entrada foi paga
        
    Returns:
        ComissaoConsultor criada ou None
    """
    # Só gera comissão se a entrada foi paga
    if not entrada_paga:
        return None
        
    # Verifica se já existe comissão para esta venda (evita duplicação)
    comissao_existente = ComissaoConsultor.objects.filter(venda=venda).first()
    if comissao_existente:
        return comissao_existente
    
    consultor = venda.usuario
    
    # Valor base é SOMENTE a entrada
    valor_entrada = venda.valor_entrada or Decimal('0')
    if valor_entrada <= 0:
        return None
    
    # Define competência (mês da entrada paga)
    competencia = timezone.now().date().replace(day=1)
    
    # Calcula faturamento total do consultor no mês (SOMENTE ENTRADAS PAGAS)
    from vendas.models import Venda
    # Considera vendas onde a entrada foi marcada como PAGA
    faturamento_mes = Venda.objects.filter(
        usuario=consultor,
        status_pagamento_entrada='PAGO',  # Apenas entradas pagas
        data_criacao__year=competencia.year,
        data_criacao__month=competencia.month
    ).aggregate(total=Sum('valor_entrada'))['total'] or Decimal('0')
    
    # Busca percentual baseado no faturamento mensal total
    percentual = obter_percentual_consultor(faturamento_mes)
    
    # Calcula valor da comissão (percentual sobre a ENTRADA)
    valor_comissao = (valor_entrada * percentual) / Decimal('100')
    
    # Cria a comissão
    comissao = ComissaoConsultor.objects.create(
        venda=venda,
        parcela=None,  # Comissão não é por parcela, é pela entrada
        consultor=consultor,
        valor=valor_comissao,
        valor_venda=valor_entrada,  # Armazena o valor da entrada
        percentual=percentual,
        status='DISPONIVEL',
        competencia=competencia
    )
    
    return comissao


def gerar_comissao_venda_captador(venda, parcela):
    """
    Gera comissão para captador quando entrada ou parcela é paga
    
    REGRA: 3% sobre valores pagos (entrada + parcelas)
    Cada pagamento gera uma comissão individual
    
    Args:
        venda: Instância da Venda
        parcela: Instância da Parcela que foi paga
        
    Returns:
        ComissaoCaptador criada ou None
    """
    # Verifica se a venda tem captador
    if not venda.captador:
        return None
    
    captador = venda.captador
    
    # Verifica se já existe comissão para esta parcela específica
    comissao_existente = ComissaoCaptador.objects.filter(
        venda=venda, 
        parcela=parcela
    ).first()
    if comissao_existente:
        return comissao_existente
    
    # Valor base é o valor da parcela paga
    valor_base = parcela.valor
    
    # Percentual fixo de 3%
    percentual = Decimal('3.0')
    
    # Calcula valor da comissão
    valor_comissao = (valor_base * percentual) / Decimal('100')
    
    # Define competência
    competencia = timezone.now().date().replace(day=1)
    
    # Cria a comissão
    comissao = ComissaoCaptador.objects.create(
        venda=venda,
        parcela=parcela,
        captador=captador,
        valor=valor_comissao,
        valor_venda=valor_base,
        percentual=percentual,
        status='DISPONIVEL',
        competencia=competencia
    )
    
    return comissao


def obter_percentual_consultor(faturamento_mensal):
    """
    Obtém o percentual de comissão do consultor baseado no faturamento mensal total
    
    REGRA: Percentual progressivo aplicado retroativamente sobre todo o faturamento
    - Faturamento ≥ R$ 20.000 = 2%
    - Faturamento ≥ R$ 30.000 = 3%
    - Faturamento ≥ R$ 40.000 = 4%
    - Faturamento ≥ R$ 50.000 = 5%
    - Faturamento ≥ R$ 60.000 = 6%
    - Faturamento ≥ R$ 80.000 = 10%
    
    Args:
        faturamento_mensal: Valor total de entradas recebidas no mês
        
    Returns:
        Decimal com o percentual
    """
    faturamento = Decimal(str(faturamento_mensal))
    
    if faturamento >= Decimal('80000'):
        return Decimal('10.0')
    elif faturamento >= Decimal('60000'):
        return Decimal('6.0')
    elif faturamento >= Decimal('50000'):
        return Decimal('5.0')
    elif faturamento >= Decimal('40000'):
        return Decimal('4.0')
    elif faturamento >= Decimal('30000'):
        return Decimal('3.0')
    elif faturamento >= Decimal('20000'):
        return Decimal('2.0')
    else:
        return Decimal('0.0')  # Sem comissão abaixo de R$ 20.000


@transaction.atomic
def autorizar_comissao(comissao_id, tipo_comissao, usuario):
    """
    Autoriza uma comissão para pagamento
    
    Args:
        comissao_id: ID da comissão
        tipo_comissao: 'lead', 'atendente', 'consultor' ou 'captador'
        usuario: Usuário que está autorizando
        
    Returns:
        Comissão atualizada ou None
    """
    model_map = {
        'lead': ComissaoLead,
        'atendente': ComissaoLead,  # Sinônimo de 'lead'
        'consultor': ComissaoConsultor,
        'captador': ComissaoCaptador
    }
    
    Model = model_map.get(tipo_comissao)
    if not Model:
        return None
    
    try:
        comissao = Model.objects.get(id=comissao_id, status='DISPONIVEL')
        comissao.status = 'AUTORIZADO'
        comissao.data_autorizacao = timezone.now()
        comissao.autorizado_por = usuario
        comissao.save()
        return comissao
    except Model.DoesNotExist:
        return None


@transaction.atomic
def processar_pagamento_comissao(comissao_id, tipo_comissao, usuario):
    """
    Processa o pagamento de uma comissão
    
    Args:
        comissao_id: ID da comissão
        tipo_comissao: 'lead', 'atendente', 'consultor' ou 'captador'
        usuario: Usuário que está processando o pagamento
        
    Returns:
        Comissão atualizada ou None
    """
    model_map = {
        'lead': ComissaoLead,
        'atendente': ComissaoLead,  # Sinônimo de 'lead'
        'consultor': ComissaoConsultor,
        'captador': ComissaoCaptador
    }
    
    Model = model_map.get(tipo_comissao)
    if not Model:
        return None
    
    try:
        comissao = Model.objects.get(id=comissao_id, status='AUTORIZADO')
        comissao.status = 'PAGO'
        comissao.data_pagamento = timezone.now().date()
        comissao.pago_por = usuario
        comissao.save()
        return comissao
    except Model.DoesNotExist:
        return None


@transaction.atomic
def cancelar_comissao(comissao_id, tipo_comissao, usuario, motivo=''):
    """
    Cancela uma comissão
    
    Args:
        comissao_id: ID da comissão
        tipo_comissao: 'lead', 'atendente', 'consultor' ou 'captador'
        usuario: Usuário que está cancelando
        motivo: Motivo do cancelamento
        
    Returns:
        Comissão atualizada ou None
    """
    model_map = {
        'lead': ComissaoLead,
        'atendente': ComissaoLead,  # Sinônimo de 'lead'
        'consultor': ComissaoConsultor,
        'captador': ComissaoCaptador
    }
    
    Model = model_map.get(tipo_comissao)
    if not Model:
        return None
    
    try:
        comissao = Model.objects.get(id=comissao_id)
        if comissao.status == 'PAGO':
            return None  # Não pode cancelar comissão já paga
        
        comissao.status = 'CANCELADO'
        comissao.observacoes = f"Cancelado por {usuario.get_full_name() or usuario.username}\nMotivo: {motivo}\n{comissao.observacoes}"
        comissao.save()
        return comissao
    except Model.DoesNotExist:
        return None


def obter_estatisticas_comissoes(tipo_comissao=None, competencia=None):
    """
    Obtém estatísticas das comissões
    
    Args:
        tipo_comissao: 'lead', 'atendente', 'consultor', 'captador' ou None (todas)
        competencia: Data de competência ou None
        
    Returns:
        Dict com estatísticas
    """
    from django.db.models import Sum, Count
    from financeiro.models import Comissao as ComissaoFinanceiro
    
    stats = {
        'disponiveis': {'count': 0, 'valor': Decimal('0')},
        'autorizados': {'count': 0, 'valor': Decimal('0')},
        'pagos': {'count': 0, 'valor': Decimal('0')},
        'cancelados': {'count': 0, 'valor': Decimal('0')},
        'total': {'count': 0, 'valor': Decimal('0')},
    }
    
    # Para captador, usar modelo financeiro.Comissao
    if tipo_comissao == 'captador':
        queryset = ComissaoFinanceiro.objects.filter(
            tipo_comissao__in=['CAPTADOR_ENTRADA', 'CAPTADOR_PARCELA']
        )
        
        # Mapear status do modelo financeiro para estatísticas
        for status_db, status_label in [('pendente', 'disponiveis'), ('paga', 'pagos'), 
                                         ('cancelada', 'cancelados')]:
            resultado = queryset.filter(status=status_db).aggregate(
                total_count=Count('id'),
                total_valor=Sum('valor_comissao')
            )
            stats[status_label]['count'] += resultado['total_count'] or 0
            stats[status_label]['valor'] += resultado['total_valor'] or Decimal('0')
    else:
        # Para lead/atendente e consultor, usar modelos antigos
        models = []
        if tipo_comissao in ['lead', 'atendente']:
            models = [ComissaoLead]
        elif tipo_comissao == 'consultor':
            models = [ComissaoConsultor]
        else:
            models = [ComissaoLead, ComissaoConsultor]
        
        for Model in models:
            queryset = Model.objects.all()
            
            if competencia:
                queryset = queryset.filter(competencia=competencia)
            
            for status_key, status_label in [('DISPONIVEL', 'disponiveis'), ('AUTORIZADO', 'autorizados'), 
                                              ('PAGO', 'pagos'), ('CANCELADO', 'cancelados')]:
                resultado = queryset.filter(status=status_key).aggregate(
                    total_count=Count('id'),
                    total_valor=Sum('valor')
                )
                stats[status_label]['count'] += resultado['total_count'] or 0
                stats[status_label]['valor'] += resultado['total_valor'] or Decimal('0')
    
    # Calcula totais
    for key in ['disponiveis', 'autorizados', 'pagos', 'cancelados']:
        stats['total']['count'] += stats[key]['count']
        stats['total']['valor'] += stats[key]['valor']
    
    return stats
