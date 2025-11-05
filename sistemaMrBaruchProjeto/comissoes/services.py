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


def gerar_comissao_venda_consultor(venda, parcela=None):
    """
    Gera comissão para consultor quando venda ou parcela é paga
    
    Args:
        venda: Instância da Venda
        parcela: Instância da Parcela (opcional)
        
    Returns:
        ComissaoConsultor criada ou None
    """
    consultor = venda.usuario
    
    # Define o valor base para cálculo
    if parcela:
        valor_base = parcela.valor
    else:
        valor_base = venda.valor_total
    
    # Busca percentual configurado (por faixa ou padrão)
    percentual = obter_percentual_consultor(venda.valor_total)
    
    # Calcula valor da comissão
    valor_comissao = (valor_base * percentual) / Decimal('100')
    
    # Define competência
    competencia = timezone.now().date().replace(day=1)
    
    # Cria a comissão
    comissao = ComissaoConsultor.objects.create(
        venda=venda,
        parcela=parcela,
        consultor=consultor,
        valor=valor_comissao,
        valor_venda=valor_base,
        percentual=percentual,
        status='DISPONIVEL',
        competencia=competencia
    )
    
    return comissao


def gerar_comissao_venda_captador(venda, parcela=None):
    """
    Gera comissão para captador quando venda ou parcela é paga
    
    Args:
        venda: Instância da Venda
        parcela: Instância da Parcela (opcional)
        
    Returns:
        ComissaoCaptador criada ou None
    """
    # Verifica se a venda tem captador
    if not venda.captador:
        return None
    
    captador = venda.captador
    
    # Define o valor base para cálculo
    if parcela:
        valor_base = parcela.valor
    else:
        valor_base = venda.valor_total
    
    # Busca percentual do captador
    percentual = captador.percentual_comissao or Decimal('0')
    
    if percentual <= 0:
        return None
    
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


def obter_percentual_consultor(valor_venda):
    """
    Obtém o percentual de comissão do consultor baseado no valor da venda
    
    Args:
        valor_venda: Valor total da venda
        
    Returns:
        Decimal com o percentual
    """
    try:
        # Busca configuração de faixas
        config = ConfiguracaoSistema.objects.get(chave='COMISSAO_CONSULTOR_FAIXAS')
        faixas = eval(config.valor)  # {"ate_10000": 5.0, "ate_30000": 7.0, "acima_30000": 10.0}
        
        valor_venda = Decimal(str(valor_venda))
        
        if valor_venda <= Decimal('10000'):
            return Decimal(str(faixas.get('ate_10000', 5.0)))
        elif valor_venda <= Decimal('30000'):
            return Decimal(str(faixas.get('ate_30000', 7.0)))
        else:
            return Decimal(str(faixas.get('acima_30000', 10.0)))
            
    except ConfiguracaoSistema.DoesNotExist:
        # Valor padrão
        return Decimal('5.0')
    except Exception:
        return Decimal('5.0')


@transaction.atomic
def autorizar_comissao(comissao_id, tipo_comissao, usuario):
    """
    Autoriza uma comissão para pagamento
    
    Args:
        comissao_id: ID da comissão
        tipo_comissao: 'lead', 'consultor' ou 'captador'
        usuario: Usuário que está autorizando
        
    Returns:
        Comissão atualizada ou None
    """
    model_map = {
        'lead': ComissaoLead,
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
        tipo_comissao: 'lead', 'consultor' ou 'captador'
        usuario: Usuário que está processando o pagamento
        
    Returns:
        Comissão atualizada ou None
    """
    model_map = {
        'lead': ComissaoLead,
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
        tipo_comissao: 'lead', 'consultor' ou 'captador'
        usuario: Usuário que está cancelando
        motivo: Motivo do cancelamento
        
    Returns:
        Comissão atualizada ou None
    """
    model_map = {
        'lead': ComissaoLead,
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
        tipo_comissao: 'lead', 'consultor', 'captador' ou None (todas)
        competencia: Data de competência ou None
        
    Returns:
        Dict com estatísticas
    """
    from django.db.models import Sum, Count
    
    stats = {
        'disponiveis': {'count': 0, 'valor': Decimal('0')},
        'autorizados': {'count': 0, 'valor': Decimal('0')},
        'pagos': {'count': 0, 'valor': Decimal('0')},
        'cancelados': {'count': 0, 'valor': Decimal('0')},
        'total': {'count': 0, 'valor': Decimal('0')},
    }
    
    models = []
    if tipo_comissao == 'lead':
        models = [ComissaoLead]
    elif tipo_comissao == 'consultor':
        models = [ComissaoConsultor]
    elif tipo_comissao == 'captador':
        models = [ComissaoCaptador]
    else:
        models = [ComissaoLead, ComissaoConsultor, ComissaoCaptador]
    
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
